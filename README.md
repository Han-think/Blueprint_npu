# NPU Inference Template (OpenVINO)

Profile로 설정 → 모델 다운로드/Export(선택) → FastAPI 서버 → `/health`, `/v1/infer`.

## Quickstart (Windows)
```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -U pip && pip install -r requirements.txt
copy .env.example .env
uvicorn src.api.server:app --reload --port 9100
curl http://127.0.0.1:9100/health
```

## Optional: OpenVINO / NPU
```bash
pip install -r requirements.txt
python scripts/setup_model.py --profile profiles/example-llm.yaml
python -m src.export.export_ov --ckpt checkpoints/epoch1 --out exports/gpt_ov
```

## Environment variables
- `OV_XML_PATH`: OpenVINO IR xml 경로
- `OV_DEVICE`: `NPU|AUTO|CPU`
- `ALLOW_FAKE_GEN=1`: 모델 없을 때 스모크용 가짜 응답

Swagger UI: http://127.0.0.1:9100/docs
