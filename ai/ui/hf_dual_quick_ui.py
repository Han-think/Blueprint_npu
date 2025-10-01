import os, subprocess, textwrap
from pathlib import Path
import gradio as gr

# ---------------------- Utils ----------------------
def _clean(txt:str)->str:
    bad = ("[LOG]", "DeprecationWarning:", "openvino\\runtime\\__init__.py")
    lines=[]
    for ln in (txt or "").splitlines():
        if any(b in ln for b in bad):  # 필터
            continue
        lines.append(ln)
    return "\n".join(lines).strip()

def _offline_env(mode:str)->dict:
    env=os.environ.copy()
    if mode in ("on","true","1"):
        env.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_DATASETS_OFFLINE":"1"})
    elif mode=="auto":
        try:
            import socket; s=socket.create_connection(("huggingface.co",443),timeout=0.8); s.close()
        except Exception:
            env.update({"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_DATASETS_OFFLINE":"1"})
    # 경고 숨김
    env["PYTHONWARNINGS"]="ignore::DeprecationWarning"
    env["PYTHONUTF8"]="1"; env["PYTHONIOENCODING"]="utf-8"
    return env

# ---------------------- Prompt Builder (AM-focused) ----------------------
def build_design_brief(
    domain, part_type, task, style, language,
    objective, perf_targets, constraints,
    am_process, material, build_vol, layer_um, min_wall_mm, min_ch_mm, tol_mm, post,
    orientation, supports, channels, test_plan, accept_criteria, extras
):
    sys = "역할: 추진/유동/적층제조 수석 엔지니어. 근거/단위/범위를 명확히."
    hdr = f"도메인:{domain} | 부품:{part_type} | 작업:{task} | 스타일:{style} | 언어:{language}"
    goal = f"목표: {objective}".strip()
    perf = f"성능목표: {perf_targets}".strip()
    cons = "설계 제약:\n- " + "\n- ".join([c.strip() for c in constraints.splitlines() if c.strip()]) if constraints.strip() else ""
    am = f"AM조건: 공정={am_process}; 재료={material}; 빌드부피={build_vol}; 층두께={layer_um}µm; 최소벽={min_wall_mm}mm; 최소채널={min_ch_mm}mm; 허용오차=±{tol_mm}mm; 후가공={post}; 방향={orientation}; 서포트={supports}; 내부채널={channels}"
    vnv = ""
    if test_plan.strip() or accept_criteria.strip():
        vnv = f"검증계획: {test_plan}\n합격기준: {accept_criteria}"
    if extras:
        vnv += ("\n추가요구: " + ", ".join(sorted(extras))) if vnv else ("추가요구: " + ", ".join(sorted(extras)))

    body = "\n".join([x for x in [sys,hdr,goal,perf,cons,am,vnv] if x])
    # 강한 프롬프트 래퍼(LLAMA 스타일)
    return f"""[SYSTEM]
{sys}
- 항목은 번호/불릿로, 중복 금지, 300~600토큰.
- 식/변수는 기호와 단위 표기(예: mm, µm, MPa, kg/s, kN).
- 가정은 근거 포함. 위험/완화책 포함.

[BRIEF]
{body}

[INSTRUCTION]
1) 핵심 아이디어/절차/체크리스트를 {style}로 출력
2) 파라미터 권장범위(+근거), 제조 리스크와 완화책, 검증 테스트를 포함
3) 제작 가능성(AM 제약)과 후가공 고려
[/INSTRUCTION]"""

def add_to_batch(batch_txt, built):  # 복사 누락 방지: 단순 합치기
    built = (built or "").strip()
    return (batch_txt + ("\n" if batch_txt and not batch_txt.endswith("\n") else "") + built) if built else batch_txt

# ---------------------- XPU (HF merged) ----------------------
_x = {"path":None,"tok":None,"model":None,"dev":"cpu","dtype":"fp32"}
def _load_xpu(merged:str,dtype:str,device:str):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    merged=str(Path(merged))
    if _x["path"]==merged and _x["model"] is not None and _x["dtype"]==dtype and _x["dev"]==device:
        return _x
    dt = torch.float32 if dtype=="fp32" else torch.bfloat16
    tok = AutoTokenizer.from_pretrained(merged, use_fast=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(merged, torch_dtype=dt, local_files_only=True).eval()
    dev = "cpu"
    if device=="auto":
        if hasattr(torch,"xpu") and torch.xpu.is_available(): dev="xpu"
        elif torch.cuda.is_available(): dev="cuda"
    else: dev=device
    try: model.to(dev)
    except Exception: dev="cpu"
    _x.update(path=merged,tok=tok,model=model,dev=dev,dtype=dtype)
    return _x

def gen_xpu(prompt, merged, max_new_tokens, dtype, device):
    if not prompt.strip(): return ""
    st=_load_xpu(merged,dtype,device)
    tok,model,dev=st["tok"],st["model"],st["dev"]
    import torch
    enc=tok(prompt, return_tensors="pt")
    if dev!="cpu":
        for k in enc: enc[k]=enc[k].to(dev)
    out=model.generate(**enc, max_new_tokens=int(max_new_tokens), do_sample=False, temperature=0.0, repetition_penalty=1.05)
    return tok.decode(out[0], skip_special_tokens=True)

# ---------------------- NPU (OpenVINO runner) ----------------------
def gen_npu(prompt, gen_py, model_dir, device, max_new_tokens, offline_mode):
    if not prompt.strip(): return ""
    py = os.environ.get("PY_EXE","python")
    env = _offline_env(offline_mode)
    # 동일 래퍼 사용(모델 일관성 증가)
    cmd=[py,"-X","utf8",gen_py,"--model_dir",model_dir,"--device",device,"--max_new_tokens",str(int(max_new_tokens)),"--prompt",prompt]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",env=env,timeout=900)
    return _clean(((r.stdout or "") + ("\n"+r.stderr if r.stderr else "")))

# ---------------------- Batch Runner ----------------------
def run_batch(prompts, run_count, gen_py, npu_model_dir, npu_device, npu_tokens, npu_offline, merged_dir, xpu_dtype, xpu_device, xpu_tokens):
    lines=[l.strip() for l in (prompts or "").splitlines() if l.strip()]
    lines=lines[:max(1,min(int(run_count),5))]
    out=[]
    for i,p in enumerate(lines,1):
        n=gen_npu(p,gen_py,npu_model_dir,npu_device,int(npu_tokens),npu_offline)
        x=gen_xpu(p,merged_dir,int(xpu_tokens),xpu_dtype,xpu_device)
        out.append(f"### {i}. Prompt\n{p}\n\n**NPU**\n```\n{n}\n```\n**XPU**\n```\n{x}\n```")
    return "\n\n---\n\n".join(out)

# ---------------------- UI ----------------------
default_prompts = """[SYSTEM]
엔지니어링 답변은 단위/근거 포함, 불릿/번호 위주, 중복 금지.
[BRIEF]
로켓 1단 효율 최적화. 재사용 고려. LPBF Ti-6Al-4V, 최소벽 0.8mm, 층두께 40µm.
목표: T/W ↑, Isp 손실 ≤3%p, 챔버 냉각 안전률 ≥1.3
제약: 직경 1.2m 이내, 내부채널 최소지름 1.5mm
[INSTRUCTION]
아이디어 3개만.
[/INSTRUCTION]
""".strip()

with gr.Blocks(title="Blueprint Dual UI v2") as demo:
    gr.Markdown("## NPU(OpenVINO) + XPU(HF) Batch Runner — v2 (Structured Design Brief)")

    with gr.Row():
        prompts = gr.Textbox(value=default_prompts, lines=18, label="Batch Prompts (1줄=1개, 최대 5개)", autogrow=True)
        run_count = gr.Slider(1,5,step=1,value=5,label="Run count (max 5)")

    with gr.Tab("Design Brief Builder (3D 금속 적층)"):
        with gr.Row():
            domain = gr.Dropdown(choices=["로켓 추진","펜슬엔진(마이크로 제트)","드론 추진","램제트"], value="로켓 추진", label="Domain")
            part_type = gr.Textbox(value="연소기/인젝터/냉각채널", label="Part type")
            task  = gr.Dropdown(choices=["아이디어","절차서","체크리스트","최적화","트러블슈팅"], value="아이디어", label="Task")
            style = gr.Dropdown(choices=["불릿","단계형(번호)","표"], value="단계형(번호)", label="Style")
            language = gr.Dropdown(choices=["한국어","영어"], value="한국어", label="Language")
        objective   = gr.Textbox(lines=2, value="Isp 손실 ≤3%p, T/W ≥120, 열안전률 ≥1.3", label="Objective")
        perf_targets= gr.Textbox(lines=2, value="챔버압 12MPa, 혼합비 3.6~3.8, 냉각채널 Δp ≤10%", label="Performance targets")
        constraints = gr.Textbox(lines=4, value="직경 ≤1.2m\n재사용 10회\n점화 안정성 유지", label="Constraints (line-separated)")
        with gr.Row():
            am_process  = gr.Dropdown(choices=["LPBF","DED","Binder Jet"], value="LPBF", label="AM process")
            material    = gr.Dropdown(choices=["Ti-6Al-4V","Inconel 718","AlSi10Mg","17-4PH"], value="Inconel 718", label="Material")
            build_vol   = gr.Textbox(value="400×400×450 mm", label="Build volume")
            layer_um    = gr.Number(value=40, label="Layer (µm)")
            min_wall_mm = gr.Number(value=0.8, label="Min wall (mm)")
            min_ch_mm   = gr.Number(value=1.5, label="Min channel (mm)")
            tol_mm      = gr.Number(value=0.1, label="Tolerance (±mm)")
            post        = gr.Textbox(value="HIP + 기계가공", label="Post-process")
        with gr.Row():
            orientation = gr.Textbox(value="채널 축을 Z축과 20~30° 경사", label="Build orientation")
            supports    = gr.Textbox(value="서포트 제거 가능한 방향으로 제한", label="Support policy")
            channels    = gr.Textbox(value="세척 가능한 개구 유지", label="Internal channels")
        with gr.Row():
            test_plan       = gr.Textbox(value="수압/헬륨 누설, 열-유로 벤치, 화재시험", label="Test plan")
            accept_criteria = gr.Textbox(value="누설=0, Δp < 규격, 열변형 < 규격", label="Acceptance criteria")
        extras = gr.CheckboxGroup(choices=["식 포함","파라미터 범위","리스크/완화책","BOM 초안","테스트 매트릭스"], value=["식 포함","파라미터 범위","리스크/완화책"], label="Extras")
        built = gr.Textbox(lines=10, label="미리보기", interactive=False, autogrow=True)
        with gr.Row():
            build_btn = gr.Button("Build brief")
            add_btn   = gr.Button("Add to Batch")
        build_btn.click(
            build_design_brief,
            [domain,part_type,task,style,language,objective,perf_targets,constraints,am_process,material,build_vol,layer_um,min_wall_mm,min_ch_mm,tol_mm,post,orientation,supports,channels,test_plan,accept_criteria,extras],
            built
        )
        add_btn.click(add_to_batch, [prompts, built], prompts)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### NPU (OpenVINO runner)")
            gen_py = gr.Textbox(value=str(Path('ai/cli/genai_run.py')), label="Generator script (genai_run.py)")
            npu_model_dir = gr.Textbox(value=str(Path('models/ov_npu_ready/llama32_1b_int4_npu_ov')), label="OV model dir")
            npu_device = gr.Dropdown(choices=["NPU","CPU","GPU"], value="NPU", label="Device")
            npu_tokens = gr.Slider(16,512,step=16,value=128,label="Max new tokens")
            npu_offline = gr.Dropdown(choices=["auto","on","off"], value="auto", label="Offline mode")
        with gr.Column():
            gr.Markdown("### XPU (HF merged)")
            merged_dir = gr.Textbox(value=str(Path('models/hf_finetuned/xpu_run1/merged')), label="Merged dir")
            xpu_dtype = gr.Dropdown(choices=["fp32","bf16"], value="fp32", label="dtype")
            xpu_device = gr.Dropdown(choices=["auto","cpu","xpu","cuda"], value="auto", label="device")
            xpu_tokens = gr.Slider(16,512,step=16,value=128,label="Max new tokens")

    run_btn = gr.Button("Run Both")
    out_md = gr.Markdown()
    run_btn.click(run_batch,
        [prompts, run_count, gen_py, npu_model_dir, npu_device, npu_tokens, npu_offline, merged_dir, xpu_dtype, xpu_device, xpu_tokens],
        [out_md])

if __name__ == "__main__":
    os.environ.setdefault("PY_EXE","python")
    demo.launch(server_name=os.environ.get("GRADIO_SERVER_NAME","127.0.0.1"),
                server_port=int(os.environ.get("GRADIO_SERVER_PORT","7860")),
                inbrowser=True, show_error=True)
