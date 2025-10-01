from huggingface_hub import snapshot_download
from pathlib import Path
root = Path(r"C:\\Users\\Lenovo\\npu-main\\Blueprint_npu")
pairs = [
  ("OpenVINO/Qwen2.5-7B-Instruct-int4-ov", "models/ov_npu_ready/qwen25_7b_int4_ov"),
  ("OpenVINO/Phi-4-mini-instruct-int4-ov","models/ov_npu_ready/phi4_mini_int4_ov"),
  ("llmware/llama-3.2-1b-instruct-npu-ov","models/ov_npu_ready/llama32_1b_int4_npu_ov"),
]
allow = [
  "openvino_model.xml","openvino_model.bin",
  "openvino_tokenizer.xml","openvino_tokenizer.bin",
  "openvino_detokenizer.xml","openvino_detokenizer.bin",
  "tokenizer.json","tokenizer.model","vocab.json","merges.txt",
  "generation_config.json","config.json","tokenizer_config.json"
]
for repo,out_rel in pairs:
    out = (root/out_rel); out.mkdir(parents=True, exist_ok=True)
    print(f"## pull {repo} -> {out}", flush=True)
    snapshot_download(repo_id=repo, local_dir=out.as_posix(),
                      local_dir_use_symlinks=False, allow_patterns=allow)
print("OK")