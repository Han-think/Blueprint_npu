from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import os, datetime

api=APIRouter(prefix="/wb")
BASE=os.path.abspath("data")
OUT =os.path.join("data","geometry","cad","saturn_stack_runs")
os.makedirs(OUT,exist_ok=True)

def _safe(rel:str):
    full=os.path.abspath(os.path.join(BASE, rel.replace("/",os.sep)))
    return full if full.startswith(BASE) else None

def _stage_specs():
    # 공용 참고치(대략): 길이[m], 직경[m], 추진제
    return [
      dict(id="S-IVB  (3rd)", L=17.8, D=6.6 , fuel="LH₂", ox="LOX", engines="J-2 x1"),
      dict(id="S-II   (2nd)", L=24.9, D=10.1, fuel="LH₂", ox="LOX", engines="J-2 x5"),
      dict(id="S-IC   (1st)", L=42.1, D=10.1, fuel="RP-1", ox="LOX", engines="F-1 x5"),
    ]

def _emit_svg(scale_len=6.0, scale_dia=10.0):
    # 스테이지를 위(S-IVB)→아래(S-IC)로 세로 스택
    specs=_stage_specs()
    pad=60
    gap=70
    W=int(1400)
    total_h=pad
    heights=[]
    for s in specs:
        h=int(s["D"]*scale_dia); heights.append(h); total_h+=h+gap
    H=total_h+pad-gap

    def X(mm): return mm
    def Y(px): return px

    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("<rect width='100%' height='100%' fill='#0c1e35'/>")
    ln.append(f"<rect x='16' y='16' width='{W-32}' height='{H-32}' fill='none' stroke='#274a79' stroke-width='2'/>")
    ln.append(f"<text x='{W-360}' y='44' fill='#ffffff' font-size='16'>SATURN V — STACK (Educational Cutaway)</text>")
    ln.append(f"<text x='{W-360}' y='64' fill='#9bd1ff' font-size='12'>Up ↑  (ascent)</text>")
    ln.append(f"<text x='{W-270}' y='64' fill='#9bd1ff' font-size='12'>Thrust ↓</text>")

    y=pad
    for idx,s in enumerate(specs):
        L=int(s["L"]*scale_len); D=int(s["D"]*scale_dia)
        x0=100; x1=x0+L; yc=y+D//2

        # 외피
        ln.append(f"<rect x='{x0}' y='{y}' width='{L}' height='{D}' fill='none' stroke='white' stroke-width='1.8'/>")
        ln.append(f"<text x='{x0}' y='{y-12}' fill='#ffffff' font-size='14'>{s['id']}  —  L≈{s['L']} m, D≈{s['D']} m, engines: {s['engines']}</text>")

        # 분리면(상하 인터스테이지)
        ln.append(f\"<line x1='{x0}' y1='{y-6}' x2='{x1}' y2='{y-6}' stroke='#6ea3e0' stroke-dasharray='6 5'/>\")

        # 탱크(교육용 단순화): LH2/LOX or RP-1/LOX 캡슐형
        # S-IVB/S-II: LH2(큰) + LOX(작은) / S-IC: LOX(큰) + RP-1(작은)
        if s["fuel"]=="LH₂":
            # LH2 앞쪽, LOX 뒤쪽
            lh2_len=int(L*0.60); lox_len=L-lh2_len- int(L*0.04)
            lh2_x=x0; lox_x=x0+lh2_len+int(L*0.04)
            def capsule(xx,ll,color):
                r=int(D*0.40)
                ln.append(f\"<path d='M {xx} {yc-r} A {r} {r} 0 0 1 {xx} {yc+r} L {xx+ll} {yc+r} A {r} {r} 0 0 1 {xx+ll} {yc-r} Z' fill='none' stroke='{color}' stroke-width='1.4'/>\")
            capsule(lh2_x,lh2_len,'#9fd3ff')
            capsule(lox_x,lox_len,'#ffd39f')
            # 배관(점선): 각각 후미 엔진 영역으로
            ex=x1; ln.append(f\"<line x1='{lh2_x+lh2_len}' y1='{yc}' x2='{ex}' y2='{yc+int(D*0.20)}' stroke='#9fd3ff' stroke-dasharray='6 4'/>\")
            ln.append(f\"<line x1='{lox_x}' y1='{yc}' x2='{ex}' y2='{yc+int(D*0.30)}' stroke='#ffd39f' stroke-dasharray='6 4'/>\")
        else:
            # S-IC: LOX 앞쪽, RP-1 뒤쪽
            lox_len=int(L*0.55); rp1_len=L-lox_len- int(L*0.04)
            lox_x=x0; rp1_x=x0+lox_len+int(L*0.04)
            def capsule(xx,ll,color):
                r=int(D*0.42)
                ln.append(f\"<path d='M {xx} {yc-r} A {r} {r} 0 0 1 {xx} {yc+r} L {xx+ll} {yc+r} A {r} {r} 0 0 1 {xx+ll} {yc-r} Z' fill='none' stroke='{color}' stroke-width='1.4'/>\")
            capsule(lox_x,lox_len,'#9fd3ff')
            capsule(rp1_x,rp1_len,'#ffa8a8')
            ex=x1; ln.append(f\"<line x1='{lox_x+lox_len}' y1='{yc}' x2='{ex}' y2='{yc+int(D*0.22)}' stroke='#9fd3ff' stroke-dasharray='6 4'/>\")
            ln.append(f\"<line x1='{rp1_x}' y1='{yc}' x2='{ex}' y2='{yc+int(D*0.32)}' stroke='#ffa8a8' stroke-dasharray='6 4'/>\")

        # 인터스테이지/스로스트영역 표시(점선 박스)
        ln.append(f\"<rect x='{int(x0+L*0.80)}' y='{y+int(D*0.15)}' width='{int(L*0.16)}' height='{int(D*0.70)}' fill='none' stroke='#e6f5a8' stroke-width='1.2' stroke-dasharray='8 4'/>\")
        ln.append(f\"<text x='{int(x0+L*0.88)}' y='{y+14}' fill='#e6f5a8' font-size='11' text-anchor='middle'>THRUST STRUCTURE</text>\")

        # 엔진 도식(아래쪽, Thrust ↓)
        def bell(cx,cy,h,w): return f\"M {cx-w//2} {cy} L {cx} {cy+h} L {cx+w//2} {cy} Z\"
        base_y=y+D+18; h=int(D*0.25); w=int(D*0.22); cx=int(x0+L*0.88)
        bells=[]
        if "x5" in s["engines"]:
            off=int(D*0.28)
            bells=[bell(cx,base_y,h,w), bell(cx-off,base_y-18,h,w), bell(cx+off,base_y-18,h,w), bell(cx-off,base_y+18,h,w), bell(cx+off,base_y+18,h,w)]
        else:
            bells=[bell(cx,base_y,h,w)]
        ln.append(f\"<path d='{' '.join(bells)}' fill='#1f6aa8' stroke='#9cd0ff' stroke-width='1'/>\")
        ln.append(f\"<text x='{cx}' y='{base_y+h+14}' fill='#9cd0ff' font-size='11' text-anchor='middle'>{s['engines']} (schematic)</text>\")

        # 치수선(길이)
        ln.append(f\"<line x1='{x0}' y1='{y+D+52}' x2='{x1}' y2='{y+D+52}' stroke='white' stroke-width='1'/>\")
        ln.append(f\"<line x1='{x0}' y1='{y+D+46}' x2='{x0}' y2='{y+D+58}' stroke='white' stroke-width='1'/>\")
        ln.append(f\"<line x1='{x1}' y1='{y+D+46}' x2='{x1}' y2='{y+D+58}' stroke='white' stroke-width='1'/>\")
        ln.append(f\"<text x='{(x0+x1)//2}' y='{y+D+40}' fill='white' font-size='12' text-anchor='middle'>L ≈ {s['L']} m</text>\")

        y += D + gap

    # 범례
    legend_x=W-280; legend_y=H-150
    ln += [
      f\"<rect x='{legend_x}' y='{legend_y}' width='240' height='120' fill='none' stroke='white' stroke-width='1'/>\",
      f\"<text x='{legend_x+10}' y='{legend_y+20}' fill='#9fd3ff' font-size='12'>LOX tank</text>\",
      f\"<text x='{legend_x+10}' y='{legend_y+38}' fill='#ffd39f' font-size='12'>LH₂ tank</text>\",
      f\"<text x='{legend_x+10}' y='{legend_y+56}' fill='#ffa8a8' font-size='12'>RP-1 tank</text>\",
      f\"<text x='{legend_x+10}' y='{legend_y+74}' fill='#e6f5a8' font-size='12'>Thrust structure</text>\",
      f\"<text x='{legend_x+10}' y='{legend_y+92}' fill='#9cd0ff' font-size='12'>Engines (schematic)</text>\",
      f\"<text x='{legend_x+10}' y='{legend_y+110}' fill='#fff' font-size='11'>REV: {datetime.date.today().isoformat()}</text>\",
    ]

    ln.append("</svg>")
    out=os.path.join(OUT, "saturn_stack_blueprint.svg")
    open(out,"w",encoding="utf-8").write("\n".join(ln))
    return out

@api.get("/cad/saturn_stack_blueprint")
def saturn_stack_blueprint():
    svg=_emit_svg()
    rel=os.path.relpath(svg,start=BASE).replace("\\","/")
    return {"ok":True,"svg_rel":rel}

@api.get("/files/{rel_path:path}")
def files(rel_path:str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full): return JSONResponse({"ok":False,"reason":"not_found"},status_code=404)
    return FileResponse(full)
