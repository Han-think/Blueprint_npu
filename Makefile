.PHONY: dev ui moo results gen bench pack test
dev:
python -m venv .venv && . .venv/bin/activate && pip install -U pip -r requirements.txt
ui:
uvicorn app.ui:app --host 127.0.0.1 --port 9030
moo:
uvicorn app.moo3:app --host 127.0.0.1 --port 9019
results:
uvicorn app.results:app --host 127.0.0.1 --port 9018
gen:
python scripts/ci_make_artifacts.py
bench:
python scripts/bench_surrogate.py --n 2048
pack:
python scripts/export_manifest.py && python scripts/release_artifacts.py
test:
pytest -q
