
# NPU Inference Template (OpenVINO)

Profile濡??ㅼ젙 ??紐⑤뜽 ?ㅼ슫濡쒕뱶/Export(?좏깮) ??FastAPI ?쒕쾭 ??`/health`, `/v1/infer`.


- 濡쒖뺄(NPU): `scripts/run.ps1`
- 紐⑤뜽 ?명똿: `scripts/setup_model.py --profile profiles/example-llm.yaml`
- OV Export(?좏깮): `python -m src.export.export_ov --ckpt checkpoints/epoch1 --out exports/gpt_ov`
- ?섍꼍蹂??
  - `OV_XML_PATH`: OpenVINO IR xml 寃쎈줈


