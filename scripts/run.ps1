$ErrorActionPreference="Stop"
if (!(Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 필요" }
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
if (-not $env:OV_DEVICE) { $env:OV_DEVICE="AUTO" }
if (-not $env:OV_CACHE_DIR) { $env:OV_CACHE_DIR=".ov_cache" }

# FAKE 모드(OV 없어도 작동). 실추론 시 비우면 됨.
if (-not $env:ALLOW_FAKE_GEN) { $env:ALLOW_FAKE_GEN="1" }
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 9100
