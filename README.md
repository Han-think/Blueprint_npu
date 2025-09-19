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
