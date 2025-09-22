# Blueprint Model — NPU Inference Template

목표: 설계 샘플 생성 → 서러게이트 예측 → 제약 검증 → 간단 최적화.
API: /health, /generate, /predict, /evaluate, /optimize

## Docker quickstart
```bash
docker build -t blueprint-npu .
docker run -p 9030:9030 -e BLUEPRINT_FAKE=1 blueprint-npu
# UI: http://127.0.0.1:9030/ui  → Generate
```
