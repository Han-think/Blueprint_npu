import argparse, json, glob, os, random, torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer, SFTConfig

def load_logs(patterns):
    recs=[]
    for pat in patterns:
        for path in glob.glob(pat):
            with open(path,"r",encoding="utf-8") as f:
                for line in f:
                    try: j=json.loads(line)
                    except: continue
                    p=j.get("prompt"); a=j.get("output")
                    if p and a: recs.append({"text": f"User: {p}\nAssistant: {a}"})
    return recs

def pick_device(precision):
    use_xpu = hasattr(torch,"xpu") and torch.xpu.is_available()
    if use_xpu: 
        dev = torch.device("xpu")
        dtype = torch.bfloat16 if precision=="bf16" else (torch.float16 if precision=="fp16" else torch.float32)
    else:
        dev = torch.device("cpu")
        # CPU는 fp32 권장
        dtype = torch.float32
    return dev, dtype, use_xpu

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--bsz", type=int, default=1)
    ap.add_argument("--grad_accum", type=int, default=16)
    ap.add_argument("--seq_len", type=int, default=1024)
    ap.add_argument("--precision", choices=["fp16","bf16","fp32"], default="fp32")
    ap.add_argument("--data_glob", default="data/memory/chatlogs/*.jsonl")
    args=ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    recs = load_logs(args.data_glob.split(";"))
    if not recs: raise SystemExit("학습 데이터가 비어있음: "+args.data_glob)
    random.shuffle(recs)
    ds = Dataset.from_list(recs)

    tok = AutoTokenizer.from_pretrained(args.base, use_fast=True)

    tok.model_max_length = args.seq_len

    if tok.pad_token is None:

        tok.pad_token = tok.eos_token
    if tok.pad_token is None: tok.pad_token = tok.eos_token

    device, dtype, use_xpu = pick_device(args.precision)
    print(f"DEVICE={device}, DTYPE={dtype}, XPU={use_xpu}", flush=True)

    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype)
    model.to(device)
    model.gradient_checkpointing_enable()

    lora=LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,
                    target_modules=["q_proj","k_proj","v_proj","o_proj","up_proj","down_proj","gate_proj"],
                    bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)

    train_cfg = SFTConfig(optim='adamw_torch', packing=False,  
        output_dir=os.path.join(args.out_dir,"lora"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bsz,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=0,
        
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        
        fp16=False, bf16=False,  # TRL 내부 AMP 사용 안 함
        gradient_checkpointing=True
    )
    # --- formatting for TRL >= 0.10 ---
    def _fmt(ex):
        if isinstance(ex, dict):
            if ex.get("text"):
                return ex["text"] if isinstance(ex["text"], str) else str(ex["text"])
            p = str(ex.get("prompt","")).strip()
            a = str(ex.get("output","")).strip()
            s = (f"[INST] {p} [/INST]\n{a}" if a else p).strip()
            return s
        elif isinstance(ex, str):
            return ex
        return ""
    trainer = SFTTrainer(model=model, train_dataset=ds,
                       args=train_cfg, formatting_func=_fmt)
    trainer.train()
    # === Save LoRA adapter & tokenizer ===
    out_lora = os.path.join(args.out_dir, "lora")
    os.makedirs(out_lora, exist_ok=True)
    trainer.model.save_pretrained(out_lora)
    tok.save_pretrained(args.out_dir)
trainer.save_model()

    # LoRA 병합 저장

    base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype)
    base.to(device)
    base = get_peft_model(base, lora)

    base.save_pretrained(merged_dir)
    tok.save_pretrained(merged_dir)
    print(f"MERGED_OUT={merged_dir}", flush=True)

if __name__=="__main__":
    main()














