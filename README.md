# Blueprint Model — Advanced NPU Template

다중 서비스 환경에서 로켓/터보팬 설계 최적화, 제약 검증, 결과 STL 내보내기, 실험 로깅을 수행하는 확장 템플릿입니다.

## 기본 Blueprint 파이프라인 (app.main)

```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -U pip && pip install -r requirements.txt
uvicorn app.main:app --reload --port 9001
curl http://127.0.0.1:9001/health
```

환경 변수:

* `BLUEPRINT_FAKE=1` – Surrogate 없이 더미 경로 사용
* `BLUEPRINT_DEVICE=NPU|GPU|CPU`
* `BLUEPRINT_TOPK=16`, `BLUEPRINT_SAMPLES=256`

## 확장 서비스 (FastAPI)

| 포트 | 모듈 | 설명 |
| --- | --- | --- |
| 9001 | `app.main:app` | 기본 Blueprint 파이프라인 |
| 9005 | `app.assembly:app` | 로켓/터보팬 조립 및 하이브리드 요약 |
| 9007 | `app.moo:app` | LHS/GA 기반 다목표 최적화 (rocket/pencil) |
| 9015 | `app.moo2:app` | NSGA-II Pareto 서비스 |
| 9019 | `app.moo3:app` | 제약 인지 NSGA-II (Deb proxy) |
| 9013 | `app.meta:app` | 단위/카탈로그/제조 규칙 메타 API |
| 9014 | `app.verify:app` | 기본 설계 검증 |
| 9016 | `app.verify2:app` | API-key 옵션 포함 엄격 검증 |
| 9017 | `app.materials:app` | 소재 데이터 조회 |
| 9018 | `app.results:app` | Pareto 결과 및 STL 다운로드 |
| 9020 | `app.metrics2:app` | 지연 히스토그램/에러 카운터 |
| 9008 | `app.geometry:app` | 노즐/덕트 STL 생성 |
| 9018 | `app.aggregate:app` | 헬스 체크 집계 |
| 9003 | `app.proof_api:app` | Proof-of-measurement 데모 |

로컬에서 여러 서비스를 동시에 띄우려면:

```bash
python scripts/run_servers.py
```

## CLI 및 스크립트

* `python scripts/bp.py moo --mode rocket --samples 256 --method lhs`
* `python scripts/run_moo_and_save.py --mode rocket --method ga`
* `python scripts/export_top_geometry.py --pareto data/pareto/latest.json`
* `python scripts/export_batch_geometry.py --pareto data/pareto/latest.json --top 5`
* `python scripts/sweep_moo.py --mode rocket --seeds 8`
* `python scripts/check_drift.py --file data/experiments/measurements.jsonl`
* `python scripts/seed_cea_table.py`
* `python scripts/calibrate_from_table.py --table data/cea/cea_table.csv`
* `python scripts/calibrate_with_rocketcea.py --samples 200`
* `python scripts/update_manifest.py`

## Proof 실험 흐름

```bash
uvicorn app.proof_api:app --reload --port 9003
python scripts/demo_proof.py --mode rocket --samples 128 --noise 0.05
python scripts/check_drift.py --file data/experiments/<run_id>/measurements.jsonl
```

`data/experiments/`는 git에서 제외되지만 README 플레이스홀더를 통해 디렉터리 구조를 유지합니다.

## STL/결과 보기

Pareto JSON을 생성한 뒤 Results API 또는 CLI를 통해 STL로 변환합니다.

```bash
python scripts/run_moo_and_save.py --mode rocket
uvicorn app.results:app --reload --port 9018
curl "http://127.0.0.1:9018/results/topstl?name=latest.json&index=0" --output nozzle.stl
```

## 테스트

```bash
pytest -q
```

또는 새 스크립트/서비스를 추가한 뒤 `python -m compileall src app`로 빠르게 문법 검사를 수행할 수 있습니다.
