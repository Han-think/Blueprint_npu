import argparse, os
from openvino_genai import LLMPipeline, GenerationConfig
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--device", default=os.getenv("OV_DEVICE","AUTO"))
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--prompt", default="테스트")
    a = ap.parse_args()
    pipe = LLMPipeline(a.model_dir, a.device)
    cfg  = GenerationConfig(max_new_tokens=a.max_new_tokens)
    out  = pipe.generate(a.prompt, generation_config=cfg)
    print(out)
if __name__ == "__main__":
    main()
