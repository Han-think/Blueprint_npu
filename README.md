# Mech-Syn Rocket (OpenVINO-ready)

프로필 설정 → 모델 다운로드(선택) → FastAPI 서버 → /health, /v1/generate.

- 로컬 실행: `scripts/run.ps1`
- 모델 세팅: `python scripts/setup_model.py --profile profiles/rocket.yaml`
- OV Export(선택): `python scripts/export_ov.py --ckpt checkpoints/epoch1 --out exports/rocket_ov`
- 환경변수:
  - OV_GEN_XML, OV_SIM_XML: OpenVINO IR xml 경로 (생성기/서로게이트)
  - OV_DEVICE: NPU|AUTO|CPU
  - ALLOW_FAKE_GEN=1 → 모델 없이도 스모크용 가짜 응답
- Swagger: http://127.0.0.1:9100/docs

`/v1/generate`는 파라미터 샘플러 → 간이 surrogate → 제약 체크 → Pareto front 인덱스를 반환합니다.
프로필/제약/재료 상수는 `profiles/rocket.yaml`에서 조정할 수 있습니다.
