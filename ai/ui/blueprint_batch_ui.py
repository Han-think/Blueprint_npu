import os, sys, json, csv, zipfile, re, io, subprocess
from pathlib import Path
from datetime import datetime
import gradio as gr

# =========================
# XPU (HF merged)
# =========================
_tok=_model=None; _src=None; _dev="cpu"
def _dtype(s):
    import torch
    return {"fp32":torch.float32,"bf16":torch.bfloat16,"f16":torch.float16}.get(str(s).lower(),torch.float32)

def load_xpu(merged_dir, dtype, device):
    global _tok,_model,_src,_dev
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    mdir=str(Path(merged_dir).resolve())
    if _model is not None and _src==mdir and _dev==device: return "ok"
    _tok   = AutoTokenizer.from_pretrained(mdir, use_fast=True, local_files_only=True)
    _model = AutoModelForCausalLM.from_pretrained(mdir, torch_dtype=_dtype(dtype), local_files_only=True).eval()
    if device.lower()=="xpu" and hasattr(torch,"xpu") and torch.xpu.is_available():
        _model.to("xpu"); _dev="xpu"
    else:
        _dev="cpu"
    _src=mdir
    return "ok"

def gen_xpu(prompt, max_new):
    if _tok is None or _model is None: return "(XPU not loaded)"
    x=_tok(prompt, return_tensors="pt")
    if _dev=="xpu": x={k:v.to("xpu") for k,v in x.items()}
    y=_model.generate(**x, max_new_tokens=int(max_new))
    return _tok.decode(y[0], skip_special_tokens=True)

# =========================
# NPU (OpenVINO runner)
# =========================
def run_npu(gen_script, ov_dir, device, max_new, prompt, offline):
    env=os.environ.copy()
    def set_off(on):
        for k in ["HF_HUB_OFFLINE","TRANSFORMERS_OFFLINE","HF_DATASETS_OFFLINE"]:
            if on: env[k]="1"
            elif k in env: env.pop(k)
    if   offline=="on" : set_off(True)
    elif offline=="off": set_off(False)
    cmd=[sys.executable, gen_script, "--model_dir", ov_dir, "--device", device,
         "--max_new_tokens", str(int(max_new)), "--prompt", prompt]
    try:
        r=subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, env=env)
        txt=(r.stdout or "")+("\n"+r.stderr if r.stderr else "")
    except Exception as e:
        txt=f"(NPU run error) {e}"
    return "\n".join([ln for ln in txt.splitlines() if not ln.startswith("[LOG]")]).strip()

# =========================
# Prompt wrapper
# =========================
WRAP_BASE = """You are a propulsion/combustion/CFD/structures integration engineer.
Goal: propose buildable ideas suited to metal additive (AM) with internal cooling/bleed channels.
Constraints:
- Numbers: ranges for T/W, Pc, OF, Tt, M, mass, heat flux, etc.
- DfAM: min channel radius, bridge/overhang angles, post-machining.
- Verification: bench steps, instrumentation points, risks & mitigations.
Format: Section headings + 3–5 bullets, 1–2 sentences/bullet with numbers.
Do not repeat these instructions; respond with sections only.
Topic: {topic}
"""
WRAP_BLUEPRINT = """Add a 'BLUEPRINT' package:
1) Design Brief
2) Part Tree (JSON fenced block named part_tree: nodes id,name,qty,material,process,children)
3) Interfaces & tolerances
4) Geometry notes (key Ø/angles/wall & channel thickness ranges)
5) Manufacturing notes (AM orientation/supports/HIP-HT/machining datums)
6) Test Plan (bench sequence, sensors, acceptance criteria)
7) Top 5 risks & probes
"""

INSTR_HINTS = [
    "You are a propulsion","당신은 추진","Add a 'BLUEPRINT'","Add a 'PROPOSAL'",
    "Format: Section headings","Constraints:"
]
def clean_text(txt:str):
    if not txt: return txt
    out=[]
    for ln in txt.splitlines():
        if any(h in ln for h in INSTR_HINTS): continue
        out.append(ln)
    s="\n".join(out)
    s=re.sub(r"(Part Tree(?: Node)*){2,}", "Part Tree", s, flags=re.I)
    return s.strip()

def wrap_prompt(raw, use_wrapper, blueprint_mode):
    topic=(raw or "").strip()
    if not use_wrapper: return topic
    t = WRAP_BASE.format(topic=topic)
    if blueprint_mode: t += "\n" + WRAP_BLUEPRINT
    return t

# =========================
# Batch / scoring / save
# =========================
def expand_lines(lines, total, cycle):
    if not lines: return []
    if not cycle: return lines[:total]
    out=[]; i=0
    while len(out)<total:
        out.append(lines[i%len(lines)])
        i+=1
    return out

_num_re = re.compile(r"\d+(\.\d+)?")
def score_block(txt:str):
    if not txt: return 0.0
    txt=clean_text(txt)
    s  = len(_num_re.findall(txt)) * 1.0
    s += 3.0 if "```part_tree" in txt.lower() or "part_tree" in txt.lower() else 0.0
    s += 1.0 if ("Test Plan" in txt or "벤치" in txt) else 0.0
    s -= 2.0 * sum(1 for h in INSTR_HINTS if h in txt)
    s -= 0.2 * txt.count("  ")
    return round(s,2)

def build_records(lines, make_npu, make_xpu, cfg):
    records=[]
    for i,topic in enumerate(lines,1):
        p = wrap_prompt(topic, cfg["use_wrap"], cfg["blueprint"])
        npu = run_npu(cfg["gen_script"], cfg["ov_dir"], cfg["npu_dev"], int(cfg["npu_max"]), p, cfg["npu_off"]) if make_npu else ""
        xpu = gen_xpu(p, int(cfg["xpu_max"])) if make_xpu else ""
        npu_c, xpu_c = clean_text(npu), clean_text(xpu)
        records.append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "idx": i, "topic": topic, "prompt_wrapped": p,
            "settings":{"npu":{"dev":cfg["npu_dev"],"max_new":int(cfg["npu_max"])}, "xpu":{"dir":cfg["merged_dir"],"dtype":cfg["xpu_dtype"],"dev":cfg["xpu_dev"],"max_new":int(cfg["xpu_max"])}},
            "npu": npu_c, "xpu": xpu_c,
            "score_npu": score_block(npu_c), "score_xpu": score_block(xpu_c)
        })
    return records

def save_session(session_name, records, keep_top=0, keep_bottom=0):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join([c for c in (session_name or "session") if c.isalnum() or c in ("-","_")]) or "session"
    root = Path("save")/"sessions"/f"{ts}_{safe}"
    root.mkdir(parents=True, exist_ok=True)
    # jsonl
    with (root/"run.jsonl").open("w", encoding="utf-8") as f:
        for r in records: f.write(json.dumps(r, ensure_ascii=False)+"\n")
    # markdown
    with (root/"run.md").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(f"### {r['idx']}. {r['topic']}\n\n**NPU(OpenVINO)**\n{r['npu'] or '(no output)'}\n\n**XPU(HF merged)**\n{r['xpu'] or '(no output)'}\n\n---\n")
    # ranking
    flat=[]
    for r in records:
        if r["npu"]: flat.append(("npu", r["score_npu"], r["topic"], r["npu"]))
        if r["xpu"]: flat.append(("xpu", r["score_xpu"], r["topic"], r["xpu"]))
    if flat:
        flat.sort(key=lambda t: t[1], reverse=True)
        if keep_top>0:
            with (root/"best.md").open("w", encoding="utf-8") as f:
                for src,sc,topic,txt in flat[:keep_top]:
                    f.write(f"## BEST [{src}] score={sc} | {topic}\n\n{txt}\n\n---\n")
        if keep_bottom>0:
            with (root/"worst.md").open("w", encoding="utf-8") as f:
                for src,sc,topic,txt in flat[-keep_bottom:]:
                    f.write(f"## WORST [{src}] score={sc} | {topic}\n\n{txt}\n\n---\n")
    return str(root)

# =========================
# Blueprint / Print-Pack export
# =========================
PT_RE = re.compile(r"```part_tree\s*(\{.*?\})\s*```", re.S|re.I)
def extract_part_tree(text):
    m = PT_RE.search(text or "")
    if not m: return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None

def flatten_bom(node, rows, parent=""):
    if not isinstance(node, dict): return
    rid = node.get("id","")
    rows.append([rid, node.get("name",""), node.get("qty",1), node.get("material",""), node.get("process",""), parent])
    for ch in (node.get("children") or []):
        flatten_bom(ch, rows, rid)

def export_blueprints(session_root:str, records, include_npu=True, include_xpu=True):
    root = Path(session_root)
    pack_dir = root/"blueprints"
    for r in records:
        for src_key, txt in (("npu", r["npu"]), ("xpu", r["xpu"])):
            if (src_key=="npu" and not include_npu) or (src_key=="xpu" and not include_xpu): 
                continue
            if not txt: continue
            topic_s = "".join([c for c in r["topic"] if c.isalnum() or c in ("-","_"," ")])[:80].strip().replace(" ","_")
            d = pack_dir/f"{r['idx']:02d}_{topic_s}"/src_key
            d.mkdir(parents=True, exist_ok=True)
            # full blueprint text
            (d/"blueprint.md").write_text(txt, encoding="utf-8")
            # part_tree -> json + bom csv
            pt = extract_part_tree(txt)
            if pt:
                (d/"part_tree.json").write_text(json.dumps(pt, ensure_ascii=False, indent=2), encoding="utf-8")
                rows=[]; flatten_bom(pt, rows)
                with (d/"BOM.csv").open("w", newline="", encoding="utf-8") as f:
                    w=csv.writer(f); w.writerow(["id","name","qty","material","process","parent"])
                    w.writerows(rows)
    # aggregate print queue
    pq = []
    for bom in pack_dir.rglob("BOM.csv"):
        with bom.open("r", encoding="utf-8") as f:
            r=csv.DictReader(f)
            for row in r:
                pq.append([row["id"], row["name"], row["qty"], row["material"], row["process"], str(bom.parent.relative_to(pack_dir))])
    if pq:
        with (pack_dir/"PRINT_QUEUE.csv").open("w", newline="", encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["id","name","qty","material","process","path"])
            w.writerows(pq)
    # zip
    zip_path = root/("print_pack.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in (root/"blueprints").rglob("*"):
            z.write(p, p.relative_to(root))
    return str(zip_path)

# =========================
# Runners
# =========================
def run_core(which, prompts_block, run_count, cycle_fill,
             gen_script, ov_dir, npu_dev, npu_max, npu_off,
             merged_dir, xpu_dtype, xpu_dev, xpu_max,
             use_wrap, blueprint, do_save, session_name, keep_top, keep_bottom):
    lines=[ln.strip() for ln in (prompts_block or "").splitlines() if ln.strip()]
    lines=expand_lines(lines, max(1,min(int(run_count),50)), cycle_fill)
    try:
        if merged_dir and (which in ("xpu","both")): load_xpu(merged_dir, xpu_dtype, xpu_dev)
    except Exception: pass
    cfg=dict(gen_script=gen_script, ov_dir=ov_dir, npu_dev=npu_dev, npu_max=npu_max, npu_off=npu_off,
             merged_dir=merged_dir, xpu_dtype=xpu_dtype, xpu_dev=xpu_dev, xpu_max=xpu_max,
             use_wrap=use_wrap, blueprint=blueprint)
    make_npu = which in ("npu","both")
    make_xpu = which in ("xpu","both")
    recs = build_records(lines, make_npu, make_xpu, cfg)
    saved_path = save_session(session_name, recs, int(keep_top), int(keep_bottom)) if do_save else ""
    out = "\n\n".join([f"### {r['idx']}. {r['topic']}\n\n**NPU(OpenVINO)**\n{r['npu'] or '(no output)'}\n\n**XPU(HF merged)**\n{r['xpu'] or '(no output)'}" for r in recs])
    if saved_path: out += f"\n\n> Saved to **{saved_path}**"
    return out, saved_path

def run_npu_only(*args):  txt, path = run_core("npu",  *args); return txt, path
def run_xpu_only(*args):  txt, path = run_core("xpu",  *args); return txt, path
def run_both   (*args):   txt, path = run_core("both", *args); return txt, path

# =========================
# UI
# =========================
with gr.Blocks(title="Blueprint NPU+XPU Batch Runner v5") as demo:
    gr.Markdown("## NPU(OpenVINO) + XPU(HF merged) — batch up to 50 · save JSONL/MD · export BLUEPRINT/Print-Pack")
    with gr.Row():
        prompts = gr.Textbox(label="Prompts (1 line = 1 task)", lines=14,
            value="Rocket stage-1 efficiency…\nLEAF71 combustion stability…\nLow-noise drone prop…\nRamjet inlet M2–4…\nPencil-engine transition…")
        run_count = gr.Slider(1,50,value=10,step=1,label="Run count (max 50)")
    cycle_fill = gr.Checkbox(value=True, label="Cycle prompts to fill run_count")

    with gr.Accordion("NPU (OpenVINO runner)", open=False):
        gen_script = gr.Textbox(label="Generator script (genai_run.py)", value="ai\\cli\\genai_run.py")
        ov_dir     = gr.Textbox(label="OV model dir", value="models\\ov_npu_ready\\llama32_1b_int4_npu_ov")
        npu_dev    = gr.Dropdown(["NPU","CPU","AUTO"], value="NPU", label="Device")
        npu_max    = gr.Slider(16,512,value=128,step=16,label="Max new tokens")
        npu_off    = gr.Dropdown(["auto","on","off"], value="auto", label="Offline mode")

    with gr.Accordion("XPU (HF merged)", open=True):
        merged_dir = gr.Textbox(label="Merged dir", value="models\\hf_finetuned\\xpu_run1\\merged")
        xpu_dtype  = gr.Dropdown(["fp32","bf16","f16"], value="fp32", label="dtype")
        xpu_dev    = gr.Dropdown(["cpu","xpu"], value="xpu", label="device")
        xpu_max    = gr.Slider(16,512,value=128,step=16,label="Max new tokens")

    with gr.Row():
        use_wrap  = gr.Checkbox(value=True,  label="Apply engineering wrapper")
        blueprint = gr.Checkbox(value=True,  label="Add BLUEPRINT package (part tree, tolerances, tests)")

    with gr.Row():
        do_save      = gr.Checkbox(value=True, label="Save to ./save/sessions")
        session_name = gr.Textbox(value="npu_xpu_batch", label="Session name")
        keep_top     = gr.Slider(0,50,value=5,step=1,label="Save top-N to best.md")
        keep_bottom  = gr.Slider(0,50,value=0,step=1,label="Save bottom-N to worst.md")

    with gr.Row():
        btn_npu  = gr.Button("Run NPU only")
        btn_xpu  = gr.Button("Run XPU only", variant="secondary")
        btn_both = gr.Button("Run Both",  variant="primary")

    out = gr.Markdown()
    sess_path = gr.Textbox(label="Session folder", interactive=False)

    # --- Artifacts tab: export blueprint / print pack ---
    with gr.Tab("Artifacts (Blueprint & Print-Pack)"):
        gr.Markdown("### Export BLUEPRINTs per model and build a printable pack (BOM/PRINT_QUEUE + zip)")
        use_npu = gr.Checkbox(value=False, label="Include NPU results")
        use_xpu = gr.Checkbox(value=True,  label="Include XPU results")
        export_btn = gr.Button("Export BLUEPRINTs / Build Print-Pack (zip)")
        zip_file = gr.File(label="download print_pack.zip", interactive=False)

        def do_export(session_folder, inc_npu, inc_xpu):
            if not session_folder or not Path(session_folder).exists():
                return None
            # load records back
            jl = Path(session_folder)/"run.jsonl"
            recs=[]
            if jl.exists():
                for ln in jl.read_text(encoding="utf-8").splitlines():
                    try: recs.append(json.loads(ln))
                    except: pass
            if not recs: return None
            zp = export_blueprints(session_folder, recs, include_npu=inc_npu, include_xpu=inc_xpu)
            return zp

        export_btn.click(do_export, [sess_path, use_npu, use_xpu], [zip_file])

    inputs=[prompts, run_count, cycle_fill,
            gen_script, ov_dir, npu_dev, npu_max, npu_off,
            merged_dir, xpu_dtype, xpu_dev, xpu_max,
            use_wrap, blueprint, do_save, session_name, keep_top, keep_bottom]

    def _wrap(fn, *args):
        txt, path = fn(*args)
        return txt, path

    btn_npu.click( lambda *a:_wrap(run_npu_only, *a), inputs, [out, sess_path])
    btn_xpu.click( lambda *a:_wrap(run_xpu_only, *a), inputs, [out, sess_path])
    btn_both.click(lambda *a:_wrap(run_both,    *a), inputs, [out, sess_path])

demo.launch(server_name=os.environ.get("GRADIO_SERVER_NAME","127.0.0.1"),
            server_port=int(os.environ.get("GRADIO_SERVER_PORT","7860")))
