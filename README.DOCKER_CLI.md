# Docker & CLI quick guide

## CLI

```
python scripts/bp.py moo --mode rocket --samples 256 --topk 16 --method lhs
python scripts/bp.py moo --mode pencil --samples 256 --topk 16 --method lhs --M0 0.9 --alt_m 2000
python scripts/bp.py export-stl --pareto data/pareto/latest.json --out nozzle_top.stl
```

## Docker

```
docker build -t blueprint-model:latest .
docker run --rm -p 9007:9007 -e BLUEPRINT_FAKE=1 blueprint-model:latest
curl http://127.0.0.1:9007/moo/health
```

