import argparse, os, subprocess, time, concurrent.futures
from datetime import datetime
from pathlib import Path
import gradio as gr

def clean(txt:str)->str:
    return "\n".join([ln for ln in txt.splitlines() if not ln.startswith("[LOG]")]).strip()

def one_job(py, gen, model_dir, device, prompt, offline:bool):
    env = os.environ.copy()
    if offline:
        env.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_DATASETS_OFFLINE":"1"})
    cmd=[py,"-X","utf8",gen,"--model_dir",model_dir,"--device",device,"--max_new_tokens","256","--prompt",prompt]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",env=env)
    out=clean(((r.stdout or "")+("\n"+r.stderr if r.stderr else ""))).strip()
    ts=datetime.now().strftime("%H:%M:%S")
    return f"[{ts}] {out or '(no output)'}"

def build_ui(args):
    seeds = "\n".join([
        "램제트 도입부 압축비 핵심 변수 3개만.",
        "소형 드론 프로펠러 저소음 설계 팁 5가지.",
        "재사용 1단 Isp 손실 3%p 줄이는 체크리스트 요약.",
        "J58 축소 시 열관리 핵심 리스크 3개.",
        "LEAF71 스타일 연소 안정화 핵심 포인트."
    ])

    with gr.Blocks(title="Dual Device 5x5 Check") as demo:
        gr.Markdown(f"**NPU 모델**: `{args.npu_model}`  |  **XPU 모델**: `{args.xpu_model}`  |  **오프라인**: `{args.offline}`")
        prompts = gr.Textbox(label="Prompts (한 줄당 1개)", value=seeds, lines=8)
        with gr.Row():
            npu_k = gr.Slider(0,5,value=5,step=1,label="NPU 동시 작업 수")
            xpu_k = gr.Slider(0,5,value=5,step=1,label="XPU 동시 작업 수")
            run_btn = gr.Button("각각 실행")
        with gr.Row():
            npu_out = gr.Textbox(label="NPU 결과", lines=18)
            xpu_out = gr.Textbox(label="XPU 결과", lines=18)
        status = gr.Markdown()

        def run_batch(prompts_text, npu_n, xpu_n):
            lines=[p.strip() for p in prompts_text.splitlines() if p.strip()]
            npu_prompts = lines[:int(npu_n)]
            xpu_prompts = lines[:int(xpu_n)]
            t0=time.time()
            max_workers=max(len(npu_prompts), len(xpu_prompts), 1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                npu_futs=[ex.submit(one_job,args.py,args.gen,args.npu_model,"NPU",p,args.offline) for p in npu_prompts]
                xpu_futs=[ex.submit(one_job,args.py,args.gen,args.xpu_model,"XPU",p,args.offline) for p in xpu_prompts]
                npu_res=[f.result() for f in npu_futs] if npu_futs else ["(no NPU jobs)"]
                xpu_res=[f.result() for f in xpu_futs] if xpu_futs else ["(no XPU jobs)"]
            return "\n\n----\n\n".join(npu_res), "\n\n----\n\n".join(xpu_res), f"완료: {time.time()-t0:.1f}s"

        run_btn.click(run_batch,[prompts,npu_k,xpu_k],[npu_out,xpu_out,status])
    demo.queue(api_open=False).launch(server_name="0.0.0.0", server_port=args.port, share=False)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--py", default=str(Path(".venv/Scripts/python.exe")))
    ap.add_argument("--gen", default=str(Path("ai/cli/genai_run.py")))
    ap.add_argument("--npu_model", default=str(Path("models/ov_npu_ready/llama32_1b_int4_npu_ov")))
    ap.add_argument("--xpu_model", default=str(Path("models/hf_finetuned/xpu_run1/merged")))
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--offline", action="store_true")
    args=ap.parse_args()
    for p in (args.npu_model, args.xpu_model, args.gen):
        if not Path(p).exists():
            raise SystemExit(f"경로가 없습니다: {p}")
    build_ui(args)
