import gradio as gr, json, glob, os, pandas as pd, pathlib
def latest_run():
    paths=sorted(glob.glob("save/sessions/*_dual_batch_v3/run.jsonl"), key=os.path.getmtime)
    return paths[-1] if paths else ""
def load_jsonl(p):
    recs=[]
    for ln in open(p,encoding="utf-8"):
        recs.append(json.loads(ln))
    return recs
def table_src(p):
    recs=load_jsonl(p)
    rows=[]
    for i,r in enumerate(recs,1):
        rows.append({
            "#":i, "topic":r["topic"], "elapsed":r["elapsed_sec"],
            "ov_pass": int(r["qa"]["ov"]["pass"]), "hf_pass": int(r["qa"]["hf"]["pass"])
        })
    return pd.DataFrame(rows)
def read_detail(p, idx):
    recs=load_jsonl(p); i=int(idx)-1
    if i<0 or i>=len(recs): return "", "", ""
    r=recs[i]
    return r["topic"], r["ov"]["out"], r["hf"]["out"]
def app():
    with gr.Blocks() as demo:
        gr.Markdown("# Dual Batch v3 Viewer")
        run_path=gr.Textbox(value=latest_run(), label="run.jsonl path")
        btn=gr.Button("Load")
        tbl=gr.Dataframe(headers=["#","topic","elapsed","ov_pass","hf_pass"], interactive=False)
        idx=gr.Number(value=1, precision=0, label="row #")
        topic=gr.Textbox(label="topic")
        ov=gr.Markdown(label="ov_out")
        hf=gr.Markdown(label="hf_out")
        def _load(p): 
            import pandas as pd
            return table_src(p)
        btn.click(_load, inputs=run_path, outputs=tbl)
        idx.change(read_detail, inputs=[run_path,idx], outputs=[topic,ov,hf])
    return demo
if __name__ == "__main__":
    app().launch(server_name="127.0.0.1", server_port=9036)
