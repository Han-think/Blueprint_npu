import json, re, sys, pathlib, csv
p = pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else None
if not p or not p.exists(): sys.exit("usage: python tools/validate_outputs.py <run.jsonl>")
NEED = ["Design Brief","Part Tree","Interfaces","Geometry","Manufacturing","Test Plan","Top 5 risks","Verification plan","Verification results","Final"]
rows=[]
for ln in p.read_text(encoding="utf-8").splitlines():
    r=json.loads(ln)
    txt=(r.get("ov",{}).get("out","")+"\n"+r.get("hf",{}).get("out",""))
    found=[k for k in NEED if re.search(rf"{re.escape(k)}",txt,re.I)]
    has_pt = "```" in txt and "part_tree" in txt
    dedup = len(re.findall(r"Design Brief",txt,re.I))<=2
    ok = (len(found)>=8) and has_pt and dedup
    rows.append([r["topic"],int(ok),len(found),int(has_pt),int(dedup)])
out = p.with_suffix(".extqa.md")
with open(out,"w",encoding="utf-8") as f:
    f.write("|topic|pass|sections|part_tree|dedup|\n|:-|:-:|:-:|:-:|:-:|\n")
    for r in rows: f.write(f"|{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|\n")
print(f"QA -> {out}")
