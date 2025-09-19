# NPU Inference Template (OpenVINO)

OpenVINO IR 자산을 프로파일 기반으로 다운로드한 뒤 FastAPI 서버(`/health`, `/v1/infer`)에서 추론을 제공합니다. 모델이 없는 환경에서는 `ALLOW_FAKE_GEN=1`을 이용해 스모크 테스트용 가짜 응답을 반환할 수 있습니다.

## Quickstart

1. **모델 다운로드**
   ```bash
   python scripts/setup_model.py --profile profiles/example-llm.yaml
   ```
   - `profiles/example-llm.yaml` 은 Hugging Face 상의 OpenVINO GenAI 자산을 로컬 `models/` 폴더로 받습니다.
   - 다운로드가 완료되면 `OV_XML_PATH=<경로>` 힌트를 출력합니다. 필요 시 `OV_MODEL_DIR` 환경변수로 폴더를 직접 지정할 수 있습니다.

2. **(선택) PyTorch → OpenVINO IR Export**
   ```bash
   python -m src.export.export_ov --ckpt checkpoints/epoch1 --out exports/gpt_ov
   ```
   - `optimum-intel` 의 OpenVINO 익스포터를 래핑합니다. `--task text-generation-with-past` 를 우선 시도하고 실패하면 기본 `text-generation` 작업으로 재시도합니다.

3. **서버 실행**
   - PowerShell: `scripts/run.ps1`
   - 수동 실행 예시
     ```bash
     export ALLOW_FAKE_GEN=1      # 모델 없이도 동작 확인 (선택)
     export OV_XML_PATH=exports/gpt_ov/openvino_model.xml
     export OV_DEVICE=AUTO        # NPU|AUTO|CPU
     python -m uvicorn src.api.server:app --host 127.0.0.1 --port 9100
     ```

4. **API 사용**
   ```bash
   curl -X POST http://127.0.0.1:9100/v1/infer \
     -H "content-type: application/json" \
     -d '{"prompt":"Hello OpenVINO","max_new_tokens":32}'
   ```

## 주요 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `ALLOW_FAKE_GEN` | `1`이면 모델이 없을 때도 가짜 응답을 반환 | `0` |
| `OV_XML_PATH` | OpenVINO IR(xml) 위치. 미설정 시 `exports/`, `models/` 폴더를 검색 | 자동 검색 |
| `OV_MODEL_DIR` | OpenVINO GenAI 모델 디렉터리(선택). 지정 시 `OV_XML_PATH`보다 우선 | `None` |
| `OV_DEVICE` | OpenVINO 디바이스 힌트 (예: `NPU`, `AUTO`, `CPU`) | `AUTO` |
| `OV_CACHE_DIR` | OpenVINO 캐시 디렉터리 | `.ov_cache` |

## 참고 자료

- Swagger UI: http://127.0.0.1:9100/docs
- Smoke CI: `.github/workflows/ci.yml`
- 프로파일 예시: `profiles/example-llm.yaml`
