codex/initialize-npu-inference-template-gw57mq
# Blueprint Model — NPU Inference Template

목표: 설계 샘플 생성 → surrogate 예측 → 제약 검증 → 간단 최적화.
API: /health, /generate, /predict, /evaluate, /optimize

Quickstart (Windows):
  python -m venv .venv && . .venv/Scripts/activate
  pip install -U pip && pip install -r requirements.txt
  copy .env.example .env
  uvicorn app.main:app --reload --port 9001
  curl http://127.0.0.1:9001/health

Optional: OpenVINO / NPU:
  pip install -r requirements-ov.txt
  models/surrogate.xml, .bin 배치 시 자동 사용

Env:
  BLUEPRINT_FAKE=1        # 더미 경로
  BLUEPRINT_DEVICE=NPU|GPU|CPU
  BLUEPRINT_TOPK=16
  BLUEPRINT_SAMPLES=256

# NPU Inference Template (OpenVINO)
Profile로 설정 → 모델 다운로드/Export(선택) → FastAPI 서버 → /health, /v1/infer.
- 로컬(NPU): `scripts/run.ps1`
- 모델 세팅: `scripts/setup_model.py --profile profiles/example-llm.yaml`
- OV Export(선택): `python -m src.export.export_ov --ckpt checkpoints/epoch1 --out exports/gpt_ov`
- 환경변수:
  - OV_XML_PATH: OpenVINO IR xml 경로
  - OV_DEVICE: NPU|AUTO|CPU
  - ALLOW_FAKE_GEN=1 → 모델 없을 때 스모크용 가짜 응답
- Swagger: http://127.0.0.1:9100/docs
main
