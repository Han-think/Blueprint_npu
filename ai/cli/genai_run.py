import argparse, os, sys

def load_map(p):
    d = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"): continue
                if "=" in s:
                    k,v = s.split("=",1)
                    d[k.strip()] = os.path.expandvars(os.path.expanduser(v.strip().strip('"')))
    except FileNotFoundError:
        pass
    return d

def norm(p):
    return os.path.normpath(os.path.abspath(os.path.expanduser(os.path.expandvars(p))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", help="직접 경로 지정")
    ap.add_argument("--model", help="configs/models.txt의 키")
    ap.add_argument("--models_txt", default="configs/models.txt")
    ap.add_argument("--device", default=os.getenv("OV_DEVICE","AUTO"))
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--prompt", default="테스트")
    ap.add_argument("--list", action="store_true", help="키 목록 출력 후 종료")
    a = ap.parse_args()

    m = load_map(a.models_txt)
    if a.list:
        if not m:
            print("no entries"); sys.exit(0)
        w = max(len(k) for k in m)
        for k,v in m.items():
            print(f"{k:<{w}}  ->  {v}")
        sys.exit(0)

    model_dir = a.model_dir
    if not model_dir and a.model:
        if a.model not in m:
            print(f"[ERR] unknown model key: {a.model}. Use --list to see keys.", file=sys.stderr)
            sys.exit(2)
        model_dir = m[a.model]
    if not model_dir:
        ap.error("one of --model_dir or --model is required")

    model_dir = norm(model_dir)

    from openvino_genai import LLMPipeline, GenerationConfig
    pipe = LLMPipeline(model_dir, a.device)
    cfg  = GenerationConfig(max_new_tokens=a.max_new_tokens)
    out  = pipe.generate(a.prompt, generation_config=cfg)
    print(out)

if __name__ == "__main__":
    main()
