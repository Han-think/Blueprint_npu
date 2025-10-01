import argparse, json, os, subprocess, time
from datetime import datetime

def clean(txt:str)->str:
    # [LOG] 라인은 버리고 실제 생성 텍스트만 남김
    return "\n".join([ln for ln in txt.splitlines() if not ln.startswith("[LOG]")]).strip()

def run_one(py, gen, model_dir, device, prompt, base_env):
    env = base_env.copy()
    env.update({
        "PYTHONUTF8":"1","PYTHONIOENCODING":"utf-8",
        "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_DATASETS_OFFLINE":"1"
    })
    cmd = [py,"-X","utf8",gen,"--model_dir",model_dir,"--device",device,
           "--max_new_tokens","256","--prompt",prompt]
    # ★ encoding='utf-8', errors='replace' 로 디코딩 강제
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return clean(((r.stdout or "") + ("\n"+r.stderr if r.stderr else "")))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--py", required=True)
    ap.add_argument("--gen", required=True)
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--device", default="NPU")
    ap.add_argument("--out", required=True)
    ap.add_argument("--topic", required=True)  # rocket/pencil/drone/ramjet
    a=ap.parse_args()

    seeds={
      "rocket":[
        "로켓 효율 최적화: 새턴 V와 랩터 엔진을 비교해 추력대비질량(T/W), 챔버압, 혼합비 관점에서 개선 아이디어 10개.",
        "LEAF71 스타일의 연소안정화와 냉각 채널 설계를 소추력 엔진에 이식하는 설계 절차를 단계별 서술.",
        "재사용형 1단 추진계에서 Isp 손실을 3%p 줄이는 연소기/노즐 형상 튜닝 체크리스트."
      ],
      "pencil":[
        "J58 사이클을 연필 크기 마이크로 제트로 축소할 때 스풀/베어링/열관리 핵심 이슈 10개를 정리.",
        "소형 부스터-램제트 하이브리드 '펜슬엔진' 컨셉의 시동/전환 로직을 상태도와 함께 설명.",
        "마이크로 추력 벡터 제어를 위한 미세 노즐 클러스터 배치 설계 원칙."
      ],
      "drone":[
        "소형 드론 추진계의 프로펠러-모터-ESC 매칭을 효율곡선 기반으로 자동 최적화하는 알고리즘 설계.",
        "수직이착륙(VTOL) 기체에서 순항 변환 시 추진 손실 최소화를 위한 제어 전략 5가지.",
        "저소음 프로펠러 설계의 블레이드 형상·피치·RPM 트레이드오프를 정량화."
      ],
      "ramjet":[
        "램제트 도입부 압축비 향상을 위한 인렛 형상 최적화 변수 8개와 시험 매트릭스.",
        "서브스케일 램제트 연소 안정화 실험을 위한 연료 분사·스월·점화 위치 설계 가이드.",
        "램제트/스큔램 전환 조건을 마하수·동압·연료열방출률로 표준화."
      ]
    }

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    if not os.path.exists(a.out):
        with open(a.out,"wb") as f: f.write(bytes([0xEF,0xBB,0xBF]))  # BOM(윈도우 뷰어 호환)
    with open(a.out,"a",encoding="utf-8") as f:
        for p in seeds[a.topic]:
            rec={"ts":datetime.now().isoformat(timespec="seconds"),
                 "prompt":p,
                 "output":run_one(a.py,a.gen,a.model_dir,a.device,p,os.environ)}
            f.write(json.dumps(rec, ensure_ascii=False)+"\n")
            print("added:", p[:20], "...", flush=True)
            time.sleep(0.1)

if __name__=="__main__": main()
