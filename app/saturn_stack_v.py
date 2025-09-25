from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import os, datetime, math
api=APIRouter(prefix="/wb")

BASE=os.path.abspath("data")
OUT =os.path.join(BASE,"geometry","cad","saturn_stack_runs")
os.makedirs(OUT,exist_ok=True)

def _safe(rel:str):
    p=os.path.abspath(os.path.join(BASE,rel.replace("/",os.sep)))
    return p if p.startswith(BASE) else None

def _specs():
    # 길이[m], 직경[m], 추진제 구성, 엔진
    return [
      dict(id="S-IVB (3rd)", L=17.8, D=6.6 , tops="LOX", bots="LH2", engines="J-2 x1"),
      dict(id="S-II  (2nd)", L=24.9, D=10.1, tops="LOX", bots="LH2", engines="J-2 x5"),
      dict(id="S-IC  (1st)", L=42.1, D=10.1, tops="LOX", bots="RP-1", engines="F-1 x5"),
    ]

COL={"frame":"#ffffff","grid":"#274a79","txt":"#e8f2ff",
     "LOX":"#9fd3ff","LH2":"#ffd39f","RP-1":"#ffa8a8",
     "thrust":"#e6f5a8","skirt":"#c3a8ff","engine":"#1f6aa8","engine_st":"#9cd0ff"}

def _capsule_v(x, y, w, h, r, color):
    # 세로 캡슐 (x,y) = 상단 중심, w=폭, h=전체높이, r=반지름(양끝 돔)
    x0, x1 = x-w/2, x+w/2
    y0, y1 = y, y+h
    return (f"<path d='M {x0} {y0+r} A {r} {r} 0 0 1 {x0+r} {y0} L {x1-r} {y0} "
            f"A {r} {r} 0 0 1 {x1} {y0+r} L {x1} {y1-r} A {r} {r} 0 0 1 {x1-r} {y1} "
            f"L {x0+r} {y1} A {r} {r} 0 0 1 {x0} {y1-r} Z' fill='none' stroke='{color}' stroke-width='1.6'/>")

def _engine_cluster(cx, y0, w, h, n):
    def bell(cx,cy,w,h): return f"M {cx-w/2} {cy} L {cx} {cy+h} L {cx+w/2} {cy} Z"
    bells=[]
    if n==1:
        bells=[bell(cx,y0,w,h)]
    else:
        off=w*1.6
        bells=[bell(cx,y0,w,h),
               bell(cx-off,y0-12,w,h), bell(cx+off,y0-12,w,h),
               bell(cx-off,y0+14,w,h), bell(cx+off,y0+14,w,h)]
    return f"<path d='{' '.join(bells)}' fill='{COL['engine']}' stroke='{COL['engine_st']}' stroke-width='1'/>"

def _emit_svg(scale_len=10.0, scale_dia=8.0):
    specs=_specs()
    pad=60; vgap=80
    stageHs=[int(s['L']*scale_len) for s in specs]
    maxW=int(max(s['D']*scale_dia for s in specs)*1.75)
    H=pad + sum(stageHs) + vgap*(len(specs)-1) + pad + 180
    W=maxW+320

    cx= maxW//2 + 40
    y = pad

    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("<rect width='100%' height='100%' fill='#0c1e35'/>")
    ln.append(f"<rect x='16' y='16' width='{W-32}' height='{H-32}' fill='none' stroke='{COL['grid']}' stroke-width='2'/>")
    ln.append(f"<text x='{cx-60}' y='36' fill='{COL['txt']}' font-size='16'>SATURN V — Vertical Stack (Educational Cutaway)</text>")
    ln.append(f"<text x='{cx-60}' y='56' fill='{COL['txt']}' font-size='12'>Up ↑   Thrust ↓</text>")

    for s,stageH in zip(specs,stageHs):
        stageW=int(s['D']*scale_dia)
        x0=cx-stageW//2; x1=cx+stageW//2

        # 외피 + 상/하 스커트(점선)
        ln.append(f"<rect x='{x0}' y='{y}' width='{stageW}' height='{stageH}' fill='none' stroke='{COL['frame']}' stroke-width='1.8'/>")
        ln.append(f"<rect x='{x0}' y='{y}' width='{stageW}' height='{int(stageH*0.07)}' fill='none' stroke='{COL['skirt']}' stroke-width='1.2' stroke-dasharray='8 4'/>")
        ln.append(f"<rect x='{x0}' y='{int(y+stageH*0.86)}' width='{stageW}' height='{int(stageH*0.10)}' fill='none' stroke='{COL['skirt']}' stroke-width='1.2' stroke-dasharray='8 4'/>")
        ln.append(f"<text x='{x1+12}' y='{y+14}' fill='{COL['txt']}' font-size='13'>{s['id']}  L≈{s['L']} m  D≈{s['D']} m</text>")

        # 탱크 배치(위 tops, 아래 bots)
        gap= int(stageH*0.04)
        topH= int(stageH*0.40 if s['tops']=='LOX' and s['bots']=='LH2' else stageH*0.55)  # S-IC LOX 큼
        botH= stageH - topH - gap
        r= int(min(stageW*0.32, topH*0.35))

        ln.append(_capsule_v(cx, y, stageW, topH, r, COL[s['tops']]))
        ln.append(_capsule_v(cx, y+topH+gap, stageW, botH, r, COL[s['bots']]))

        # 인터스테이지/스로스트 구조(하단 박스)
        thrustY = int(y + stageH*0.80)
        ln.append(f"<rect x='{x0+int(stageW*0.10)}' y='{thrustY}' width='{int(stageW*0.80)}' height='{int(stageH*0.12)}' fill='none' stroke='{COL['thrust']}' stroke-width='1.2' stroke-dasharray='8 4'/>")
        ln.append(f"<text x='{cx}' y='{thrustY-6}' fill='{COL['thrust']}' font-size='11' text-anchor='middle'>THRUST STRUCTURE</text>")

        # 배관(탑/바텀→스로스트 구조)
        ln.append(f"<line x1='{cx}' y1='{y+topH}' x2='{cx}' y2='{thrustY}' stroke='{COL[s['tops']]}' stroke-dasharray='6 4'/>")
        ln.append(f"<line x1='{cx}' y1='{y+topH+gap}' x2='{cx}' y2='{thrustY}' stroke='{COL[s['bots']]}' stroke-dasharray='6 4'/>")

        # 엔진(스테이지 바닥 아래)
        eY = int(y + stageH + 20)
        n  = 5 if "x5" in s['engines'] else 1
        w  = int(stageW*0.24); h=int(stageW*0.28)
        ln.append(_engine_cluster(cx, eY, w, h, n))
        ln.append(f"<text x='{cx}' y='{eY+h+14}' fill='{COL['engine_st']}' font-size='11' text-anchor='middle'>{s['engines']} (schematic)</text>")

        # 길이 치수
        ln.append(f"<line x1='{x1+40}' y1='{y}' x2='{x1+40}' y2='{y+stageH}' stroke='{COL['frame']}' stroke-width='1'/>")
        ln.append(f"<line x1='{x1+34}' y1='{y}' x2='{x1+46}' y2='{y}' stroke='{COL['frame']}' stroke-width='1'/>")
        ln.append(f"<line x1='{x1+34}' y1='{y+stageH}' x2='{x1+46}' y2='{y+stageH}' stroke='{COL['frame']}' stroke-width='1'/>")
        ln.append(f"<text x='{x1+38}' y='{y+stageH/2}' fill='{COL['txt']}' font-size='12' dominant-baseline='middle' transform='rotate(-90 {x1+38} {y+stageH/2})'>L ≈ {s['L']} m</text>")

        y += stageH + vgap

    # 범례
    lx=W-260; ly=H-150
    ln += [
      f"<rect x='{lx}' y='{ly}' width='230' height='120' fill='none' stroke='{COL['frame']}' stroke-width='1'/>",
      f"<text x='{lx+10}' y='{ly+20}' fill='{COL['LOX']}' font-size='12'>LOX tank</text>",
      f"<text x='{lx+10}' y='{ly+38}' fill='{COL['LH2']}' font-size='12'>LH₂ tank</text>",
      f"<text x='{lx+10}' y='{ly+56}' fill='{COL['RP-1']}' font-size='12'>RP-1 tank</text>",
      f"<text x='{lx+10}' y='{ly+74}' fill='{COL['thrust']}' font-size='12'>Thrust structure</text>",
      f"<text x='{lx+10}' y='{ly+92}' fill='{COL['engine_st']}' font-size='12'>Engines (schematic)</text>",
      f"<text x='{lx+10}' y='{ly+110}' fill='{COL['txt']}' font-size='11'>REV: {datetime.date.today().isoformat()}</text>",
    ]

    ln.append("</svg>")
    out=os.path.join(OUT,"saturn_stack_blueprint_v.svg")
    open(out,"w",encoding="utf-8").write("\n".join(ln))
    return out

@api.get("/cad/saturn_stack_blueprint_v")
def saturn_stack_blueprint_v():
    svg=_emit_svg()
    rel=os.path.relpath(svg,start=BASE).replace("\\","/")
    return {"ok":True,"svg_rel":rel}

@api.get("/files/{rel_path:path}")
def files(rel_path:str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full): return JSONResponse({"ok":False,"reason":"not_found"},status_code=404)
    return FileResponse(full)
