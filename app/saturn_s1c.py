from __future__ import annotations
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, FileResponse
import os, math, json, datetime

api = APIRouter(prefix="/wb")
BASE = os.path.abspath("data")
RUNS = os.path.join("data","geometry","cad","saturn_s1c_runs")
os.makedirs(RUNS, exist_ok=True)

def _safe(rel:str):
    full=os.path.abspath(os.path.join(BASE, rel.replace("/", os.sep)))
    return full if full.startswith(BASE) else None

def _emit_blueprint(out_dir:str, scale_mm_per_m=20.0, D_stage_m=10.1, L_stage_m=42.0):
    # --- 스케일(mm) ---
    sx = sy = 1.2  # mm→px
    D = D_stage_m*scale_mm_per_m
    L = L_stage_m*scale_mm_per_m

    # 구간 비율(교육용 단순화)
    frac = dict(forward=0.04, lox=0.36, inter=0.05, rp1=0.35, thrust=0.08, aft=0.06)
    # 정규화
    s = sum(frac.values())
    for k in frac: frac[k] /= s

    z = 0.0
    seg=[]
    for k in ["forward","lox","inter","rp1","thrust","aft"]:
        ln = L*frac[k]; seg.append((k, z, z+ln)); z += ln

    def X(mm): return int(80 + mm*sx)
    def Y(mm): return int(80 + mm*sy)
    H = int(80 + (D+80)*sy)
    W = int(80 + (L+260)*sx)

    # 단면 윤곽 및 내부 요소
    ox, oy = X(0), Y(D/2)
    outer = dict(x0=X(0), y0=Y(0), x1=X(L), y1=Y(D))

    def capsule_path(z0,z1,rad):
        # 라운드탱크(상/하 반원 + 몸통)
        return f"M {X(z0)} {Y(D/2-rad)} A {int(rad*sy)} {int(rad*sy)} 0 0 1 {X(z0)} {Y(D/2+rad)} L {X(z1)} {Y(D/2+rad)} A {int(rad*sy)} {int(rad*sy)} 0 0 1 {X(z1)} {Y(D/2-rad)} Z"

    # 엔진(5기) 단순화: 후미 스커트 내부에 벨 형상 아이콘
    def engine_bell(cx, cy, h, w):
        a=f"M {cx-w//2} {cy} L {cx} {cy+h} L {cx+w//2} {cy} Z"
        return a

    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("<rect width='100%' height='100%' fill='#0c1e35'/>")
    ln.append(f"<rect x='16' y='16' width='{W-32}' height='{H-32}' fill='none' stroke='#274a79' stroke-width='2'/>")

    # 중심선
    ln.append(f"<line x1='{ox}' y1='{oy}' x2='{X(L)}' y2='{oy}' stroke='#6ea3e0' stroke-width='1' stroke-dasharray='6 4'/>")

    # 외피
    ln.append(f"<rect x='{outer['x0']}' y='{outer['y0']}' width='{outer['x1']-outer['x0']}' height='{outer['y1']-outer['y0']}' fill='none' stroke='white' stroke-width='1.8'/>")

    # LOX/RP-1 탱크(캡슐)
    zf, zt = [s for s in seg if s[0]=="lox"][0][1:]; zf1=[s for s in seg if s[0]=="lox"][0][2]
    rf = D*0.40*0.5  # 반지름(여유)
    ln.append(f"<path d='{capsule_path(zf, zf1, rf)}' fill='none' stroke='#9fd3ff' stroke-width='1.4'/>")
    zf, zt = [s for s in seg if s[0]=="rp1"][0][1:]; zf1=[s for s in seg if s[0]=="rp1"][0][2]
    rr = D*0.50*0.5
    ln.append(f"<path d='{capsule_path(zf, zf1, rr)}' fill='none' stroke='#ffd39f' stroke-width='1.4'/>")

    # 인터탱크/스커트/스로스트 구조(링)
    def ring(z0,z1,label,color):
        ln.append(f"<rect x='{X(z0)}' y='{Y(D*0.15)}' width='{X(z1)-X(z0)}' height='{int(D*0.70*sy)}' fill='none' stroke='{color}' stroke-width='1.2' stroke-dasharray='8 4'/>")
        ln.append(f"<text x='{(X(z0)+X(z1))//2}' y='{Y(D*0.15)-10}' fill='{color}' font-size='12' text-anchor='middle'>{label}</text>")

    z0,z1=[s for s in seg if s[0]=="inter"][0][1:]
    ring(z0,z1,"INTERTANK","#89ffa8")
    z0,z1=[s for s in seg if s[0]=="thrust"][0][1:]
    ring(z0,z1,"THRUST STRUCTURE","#f0ffa8")
    z0,z1=[s for s in seg if s[0]=="forward"][0][1:]
    ring(z0,z1,"FORWARD SKIRT","#caa9ff")
    z0,z1=[s for s in seg if s[0]=="aft"][0][1:]
    ring(z0,z1,"AFT SKIRT","#caa9ff")

    # 엔진 벨 5기(후미 쪽)
    aft0,aft1=[s for s in seg if s[0]=="aft"][0][1:]
    cz = X((aft0+aft1)*0.5)
    base_y = Y(D*0.72)
    h = int(D*0.18*sy); w=int(D*0.18*sx)
    offs = int(D*0.18*sx)
    bells=[
        engine_bell(cz, base_y, h, w),
        engine_bell(cz-offs, base_y-20, h, w),
        engine_bell(cz+offs, base_y-20, h, w),
        engine_bell(cz-offs, base_y+20, h, w),
        engine_bell(cz+offs, base_y+20, h, w),
    ]
    ln.append(f"<path d='{' '.join(bells)}' fill='#1f6aa8' stroke='#9cd0ff' stroke-width='1' opacity='0.9'/>")
    ln.append(f"<text x='{cz}' y='{base_y+h+16}' fill='#9cd0ff' font-size='12' text-anchor='middle'>F-1 ENGINE (SCHEMATIC x5)</text>")

    # 치수
    def dim_h(x0,x1,y,label):
        ln.append(f"<line x1='{x0}' y1='{y}' x2='{x1}' y2='{y}' stroke='white' stroke-width='1'/>")
        ln.append(f"<line x1='{x0}' y1='{y-6}' x2='{x0}' y2='{y+6}' stroke='white' stroke-width='1'/>")
        ln.append(f"<line x1='{x1}' y1='{y-6}' x2='{x1}' y2='{y+6}' stroke='white' stroke-width='1'/>")
        ln.append(f"<text x='{(x0+x1)//2}' y='{y-8}' fill='white' font-size='12' text-anchor='middle'>{label}</text>")
    def dim_v(x,y0,y1,label):
        ln.append(f"<line x1='{x}' y1='{y0}' x2='{x}' y2='{y1}' stroke='white' stroke-width='1'/>")
        ln.append(f"<line x1='{x-6}' y1='{y0}' x2='{x+6}' y2='{y0}' stroke='white' stroke-width='1'/>")
        ln.append(f"<line x1='{x-6}' y1='{y1}' x2='{x+6}' y2='{y1}' stroke='white' stroke-width='1'/>")
        ln.append(f"<text x='{x-10}' y='{(y0+y1)//2}' fill='white' font-size='12' text-anchor='end' dominant-baseline='middle'>{label}</text>")
    dim_h(X(0), X(L), Y(D)+50, f"L_stage ≈ {L_stage_m:.1f} m  (scale {scale_mm_per_m:.1f} mm/m)")
    dim_v(X(-60), Y(0), Y(D), f"D_stage ≈ {D_stage_m:.2f} m")

    # 레전드
    ln += [
      f"<rect x='{W-300}' y='{40}' width='260' height='110' fill='none' stroke='white' stroke-width='1'/>",
      f"<text x='{W-290}' y='60'  fill='white' font-size='14'>SATURN V — S-IC (Educational Cutaway)</text>",
      f"<text x='{W-290}' y='80'  fill='#9fd3ff' font-size='12'>LOX tank</text>",
      f"<text x='{W-290}' y='98'  fill='#ffd39f' font-size='12'>RP-1 tank</text>",
      f"<text x='{W-290}' y='116' fill='#89ffa8' font-size='12'>Intertank</text>",
      f"<text x='{W-290}' y='134' fill='#f0ffa8' font-size='12'>Thrust structure</text>",
      f"<text x='{W-290}' y='152' fill='#9cd0ff' font-size='12'>F-1 engine (schematic)</text>",
    ]

    ln.append("</svg>")
    out = os.path.join(out_dir, "saturn_s1c_blueprint.svg")
    open(out, "w", encoding="utf-8").write("\n".join(ln))
    return out

@api.get("/cad/saturn_s1c_blueprint")
def saturn_s1c_blueprint(scale_mm_per_m: float = 20.0, D_stage_m: float = 10.1, L_stage_m: float = 42.0):
    svg = _emit_blueprint(RUNS, scale_mm_per_m, D_stage_m, L_stage_m)
    rel = os.path.relpath(svg, start=BASE).replace("\\","/")
    return {"ok": True, "svg_rel": rel}

@api.get("/files/{rel_path:path}")
def send_file(rel_path: str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full): return JSONResponse({"ok":False,"reason":"not_found"}, status_code=404)
    return FileResponse(full)
