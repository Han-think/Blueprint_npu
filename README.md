# Blueprint Model — NPU Inference Template

목표: 설계 샘플 생성 → surrogate 예측 → 제약 검증 → 간단 최적화.
API: /health, /generate, /predict, /evaluate, /optimize

## Quickstart (Windows)
```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -U pip && pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 9001
curl http://127.0.0.1:9001/health
```

Optional: OpenVINO / NPU
```bash
pip install -r requirements-ov.txt
# models/surrogate.xml, .bin 배치 시 자동 사용
```

## Env
```
BLUEPRINT_FAKE=1      # 더미 경로
BLUEPRINT_DEVICE=NPU|GPU|CPU
BLUEPRINT_TOPK=16
BLUEPRINT_SAMPLES=256
```
