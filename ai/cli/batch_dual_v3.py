import argparse, os, sys, json, time, datetime, re, math, traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

SCHEMA_VERSION = "3"

def read_text(p):
    with open(p, encoding="utf-8") as f: return f.read()

def load_map(p):
    d={}
    try:
        with open(p, encoding="utf-8") as f:
            for ln in f:
                s=ln.strip()
                if not s or s.startswith("#"): continue
                if "=" in s:
                    k,v=s.split("=",1)
                    d[k.strip()]=os.path.expandvars(os.path.expanduser(v.strip().strip('"')))
    except FileNotFoundError: pass
    return d

def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

STRIP_PAT = re.compile(r"^(NPU\(OpenVINO\)|XPU\(HF.*\)|Goal:|Numbers:|DfAM:|Verification:|Do not repeat.*|Topic:).*", re.I)

def sanitize(txt:str)->str:
    if not isinstance(txt,str): txt=str(txt)
    lines=[]
    for ln in txt.splitlines():
        if STRIP_PAT.match(ln.strip()): continue
        lines.append(ln)
    s="\n".join(lines).strip()

    # 보정: part_tree 없으면 최소 골격 주입
    need_pt = ("```" not in s) or ("part_tree" not in s)
    if need_pt:
        skeleton = {
          "id":"root","name":"assembly","qty":1,"material":"AM-alloy",
          "process":"LPBF","children":[]
        }
        inj = "```json\npart_tree: " + json.dumps(skeleton, ensure_ascii=False) + "\n```"
        s = ("## Design Brief\n" if not s.lower().startswith("## design brief") else "") + s + "\n\n## Part Tree\n" + inj

    # 중복 헤더 줄이기
    s = re.sub(r"(\n+#\s*Design Brief[^\n]*\n)", r"\n## Design Brief\n", s, count=1, flags=re.I)
    s = re.sub(r"(\n+#\s*Design Brief[^\n]*\n)", r"\n", s, flags=re.I)
    return s.strip()

NEED_SECTIONS = [
 "Design Brief","Part Tree","Interfaces","Geometry","Manufacturing",
 "Test Plan","Top 5 risks","Verification plan","Verification results","Final"
]

def qa_score(txt:str):
    found=[k for k in NEED_SECTIONS if re.search(rf"{re.escape(k)}",txt,re.I)]
    has_pt = ("```" in txt) and ("part_tree" in txt)
    dedup = len(re.findall(r"Design Brief",txt,re.I))<=2
    pass_ = (len(found)>=8) and has_pt and dedup
    return {"pass":pass_,"sections":len(found),"part_tree":has_pt,"dedup":dedup}

# ----- OV/XPU inference -----
def ov_generate(model_dir, device, sys_txt, usr_txt, max_new_tokens, stops):
    from openvino_genai import LLMPipeline, GenerationConfig
    prompt = f"System: {sys_txt}\nUser: {usr_txt}\nAssistant:"
    cfg = GenerationConfig(max_new_tokens=max_new_tokens, stop_strings=stops)
    pipe = LLMPipeline(model_dir, device)
    return pipe.generate(prompt, generation_config=cfg)

def hf_apply_chat(tokenizer, sys_txt, usr_txt):
    if hasattr(tokenizer, "apply_chat_template"):
        msgs=[{"role":"system","content":sys_txt},{"role":"user","content":usr_txt}]
        try:
            return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass
    return f"System: {sys_txt}\nUser: {usr_txt}\nAssistant:"

def pick_hf_device(name):
    import torch
    n=name.lower()
    if n.startswith("xpu") and hasattr(torch,"xpu") and torch.xpu.is_available(): return "xpu"
    if n.startswith("cuda") and torch.cuda.is_available(): return "cuda"
    return "cpu"

def hf_generate(repo, device_name, sys_txt, usr_txt, max_new_tokens, temp, top_p, top_k, rep_pen):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = pick_hf_device(device_name)
    tok = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(repo, trust_remote_code=True)
    model.to(dev)
    if tok.pad_token_id is None and tok.eos_token_id is not None:
        tok.pad_token_id = tok.eos_token_id
    prompt = hf_apply_chat(tok, sys_txt, usr_txt)
    ids = tok(prompt, return_tensors="pt").to(dev)
    with torch.inference_mode():
        out = model.generate(
            **ids, do_sample=True, temperature=temp, top_p=top_p, top_k=top_k,
            repetition_penalty=rep_pen, max_new_tokens=max_new_tokens,
            pad_token_id=tok.pad_token_id
        )
    return tok.decode(out[0], skip_special_tokens=True)

# ----- worker with retry/timeout -----
def run_with_timeout(fn, timeout_s, retries=0):
    last_err=None
    for t in range(retries+1):
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut=ex.submit(fn)
            try:
                return fut.result(timeout=timeout_s)
            except TimeoutError:
                last_err=f"[TIMEOUT {timeout_s}s]"
            except Exception as e:
                last_err=f"[ERR] {e}"
    return last_err

def make_worker(ov_dir, hf_id, sys_txt, usr_template, args):
    stops=["Topic:","Do not repeat","XPU(","NPU("]
    def worker(topic:str):
        usr_txt = usr_template.replace("{topic}", topic)
        t0=time.time()
        def _ov(): return ov_generate(os.path.abspath(ov_dir), args.ov_device, sys_txt, usr_txt, args.max_new_tokens, stops)
        def _hf(): return hf_generate(hf_id, args.hf_device, sys_txt, usr_txt, args.max_new_tokens, args.temp, args.top_p, args.top_k, args.rep_pen)

        ov_raw = run_with_timeout(_ov, args.timeout_sec, retries=args.retries)
        hf_raw = run_with_timeout(_hf, args.timeout_sec, retries=args.retries)

        ov_txt = sanitize(ov_raw) if isinstance(ov_raw,str) else str(ov_raw)
        hf_txt = sanitize(hf_raw) if isinstance(hf_raw,str) else str(hf_raw)

        dt=round(time.time()-t0,3)
        qa = {"ov":qa_score(ov_txt), "hf":qa_score(hf_txt)}
        rec = {
            "schema":SCHEMA_VERSION, "ts":datetime.datetime.now().isoformat(timespec="seconds"),
            "topic":topic, "elapsed_sec":dt,
            "ov":{"key":args.ov_key,"device":args.ov_device,"out":ov_txt},
            "hf":{"key":args.hf_key,"device":args.hf_device,"out":hf_txt},
            "qa":qa
        }
        return rec
    return worker

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models_txt", default="configs/models.txt")
    ap.add_argument("--ov_key", default="phi4mini_ov")
    ap.add_argument("--hf_key", default="hf_small")
    ap.add_argument("--sys_template", default="prompts/sys_template.txt")
    ap.add_argument("--usr_template", default="prompts/usr_template.txt")
    ap.add_argument("--topics", default="prompts/prompts_topics.txt")
    ap.add_argument("--outdir", default="save/sessions")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--ov_device", default=os.getenv("OV_DEVICE","NPU"))
    ap.add_argument("--hf_device", default="xpu")
    ap.add_argument("--max_new_tokens", type=int, default=256)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--top_p", type=float, default=0.9)
    ap.add_argument("--top_k", type=int, default=40)
    ap.add_argument("--rep_pen", type=float, default=1.1)
    ap.add_argument("--timeout_sec", type=float, default=90)
    ap.add_argument("--retries", type=int, default=0)
    args = ap.parse_args()

    mp = load_map(args.models_txt)
    ov_dir = mp.get(args.ov_key, ""); hf_id = mp.get(args.hf_key, "")
    if not ov_dir: sys.exit(f"[ERR] unknown ov_key: {args.ov_key}")
    if not hf_id:  sys.exit(f"[ERR] unknown hf_key: {args.hf_key}")

    sys_txt = read_text(args.sys_template)
    usr_template = read_text(args.usr_template)

    topics=[]
    with open(args.topics, encoding="utf-8") as f:
        for ln in f:
            s=ln.strip()
            if s: topics.append(s)
    topics = topics[:max(0,min(args.limit,len(topics)))]

    stamp=time.strftime("%Y%m%d_%H%M%S")
    outdir=Path(args.outdir)/f"{stamp}_dual_batch_v3"
    outdir.mkdir(parents=True, exist_ok=True)
    jpath=outdir/"run.jsonl"; mpath=outdir/"run.md"; qapath=outdir/"run.qa.md"; cpath=outdir/"run.csv"

    worker = make_worker(ov_dir, hf_id, sys_txt, usr_template, args)

    rows=[]
    with ThreadPoolExecutor(max_workers=max(1,args.jobs)) as ex, open(jpath,"a",encoding="utf-8") as jf:
        futs={ ex.submit(worker, t): t for t in topics }
        for n,f in enumerate(as_completed(futs),1):
            rec=f.result()
            jf.write(json.dumps(rec,ensure_ascii=False)+"\n"); jf.flush()
            rows.append(rec)
            print(f"[{n}/{len(topics)}] {rec['topic']}  {rec['elapsed_sec']}s  qa(ov={int(rec['qa']['ov']['pass'])},hf={int(rec['qa']['hf']['pass'])})")

    # MD 요약
    def trunc(s,n=240): 
        s=s.replace("\n"," "); 
        return s if len(s)<=n else s[:n]+"…"
    with open(mpath,"w",encoding="utf-8") as mf:
        mf.write(f"# Dual Batch v3  \n- time: {now()}  \n- cnt: {len(rows)}  \n- ov={args.ov_key}({args.ov_device})  hf={args.hf_key}({args.hf_device})  \n- schema={SCHEMA_VERSION}\n\n")
        mf.write("|#|topic|ov_pass|hf_pass|elapsed(s)|ov_out|hf_out|\n|:-:|:-|:-:|:-:|:-:|:-|:-|\n")
        for i,r in enumerate(rows,1):
            mf.write(f"|{i}|{r['topic']}|{int(r['qa']['ov']['pass'])}|{int(r['qa']['hf']['pass'])}|{r['elapsed_sec']}|{trunc(r['ov']['out'])}|{trunc(r['hf']['out'])}|\n")

    # CSV
    import csv
    with open(cpath,"w",newline="",encoding="utf-8") as cf:
        w=csv.writer(cf)
        w.writerow(["idx","topic","elapsed_sec","ov_key","ov_device","ov_pass","hf_key","hf_device","hf_pass"])
        for i,r in enumerate(rows,1):
            w.writerow([i,r["topic"],r["elapsed_sec"],r["ov"]["key"],r["ov"]["device"],int(r["qa"]["ov"]["pass"]),r["hf"]["key"],r["hf"]["device"],int(r["qa"]["hf"]["pass"])])

    # QA 표
    with open(qapath,"w",encoding="utf-8") as qf:
        qf.write("|#|topic|ov_pass|ov_sections|ov_part_tree|ov_dedup|hf_pass|hf_sections|hf_part_tree|hf_dedup|\n|:-:|:-|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n")
        for i,r in enumerate(rows,1):
            o=r["qa"]["ov"]; h=r["qa"]["hf"]
            qf.write(f"|{i}|{r['topic']}|{int(o['pass'])}|{o['sections']}|{int(o['part_tree'])}|{int(o['dedup'])}|{int(h['pass'])}|{h['sections']}|{int(h['part_tree'])}|{int(h['dedup'])}|\n")

    print(f"OK -> {jpath} , {mpath} , {qapath} , {cpath}")

if __name__ == "__main__":
    main()
