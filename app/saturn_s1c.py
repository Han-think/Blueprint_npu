from __future__ import annotations
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
import os, datetime, math, json

api = APIRouter(prefix="/wb")

DATA_ROOT = os.path.join("data","geometry","cad")
RUNS_DIR  = os.path.join(DATA_ROOT, "saturn_stack_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

def _box(x,y,w,h,stroke="#fff",sw=1.6,fill="none",dash=None):
    d=f" stroke-dasharray='{dash}'" if dash else ""
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'{d}/>"

def _text(x,y,t,fs=12,fill="#fff",anc="start"):
    return f"<text x='{x}' y='{y}' fill='{fill}' font-size='{fs}' text-anchor='{anc}'>{t}</text>"

def _tri(cx,cy,w,h,stroke="#9cd0ff",fill="#1f6aa8",sw=1):
    x1,y1=cx,cy-h/2; x2,y2=cx-w/2,cy+h/2; x3,y3=cx+w/2,cy+h/2
    return f"<path d='M {x1} {y1} L {x2} {y2} L {x3} {y3} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' opacity='0.9'/>"

def _dim_h(x0,x1,y,label):
    return "\n".join([
      f"<line x1='{x0}' y1='{y}' x2='{x1}' y2='{y}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x0}' y1='{y-6}' x2='{x0}' y2='{y+6}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x1}' y1='{y-6}' x2='{x1}' y2='{y+6}' stroke='white' stroke-width='1'/>",
      f"<text x='{(x0+x1)//2}' y='{y-8}' fill='white' font-size='12' text-anchor='middle'>{label}</text>"
    ])

def _dim_v(x,y0,y1,label):
    return "\n".join([
      f"<line x1='{x}' y1='{y0}' x2='{x}' y2='{y1}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x-6}' y1='{y0}' x2='{x+6}' y2='{y0}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x-6}' y1='{y1}' x2='{x+6}' y2='{y1}' stroke='white' stroke-width='1'/>",
      f"<text x='{x-8}' y='{(y0+y1)//2}' fill='white' font-size='12' text-anchor='end' dominant-baseline='middle'>{label}</text>"
    ])

def _legend(x,y,items):
    ln=[_box(x,y,260,18*len(items)+14,stroke="#fff",sw=1,fill="none")]
    yy=y+16
    for label, color in items:
        ln.append(_box(x+10,yy-10,18,12,stroke=color,sw=2))
        ln.append(_text(x+36,yy,label,12,"#fff"))
        yy+=18
    return "\n".join(ln)

def _emit_stack_svg(out_dir:str, scale_mm_per_m:float=10.0):
    # 간단 정수 스펙(교육용): 실제 수치와 비율만 맞춤
    D_stack  = 10.1      # 전단 공통 외경(m)
    L_SIC    = 42.1      # 1단 길이(m)
    L_SII    = 24.9      # 2단 길이(m)
    L_SIVB   = 17.8      # 3단 길이(m)
    L_IU     = 0.9       # 계측유닛 (상단 링)
    GAP      = 1.2       # 스테이지 사이 시각 간격(m)

    W = 900
    H = int((L_SIC+L_SII+L_SIVB+L_IU+3*GAP)*scale_mm_per_m + 160)
    ox,oy = 150, 60
    body_w = int(D_stack*scale_mm_per_m)

    def Y(z_from_top_m): return oy + int(z_from_top_m*scale_mm_per_m)

    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("<rect width='100%' height='100%' fill='#0c1e35'/>")
    ln.append(_box(16,16,W-32,H-32,stroke='#274a79',sw=2))

    # 상단부터 누적 배치
    z=0.0
    # IU
    ln.append(_box(ox, Y(z), body_w, int(L_IU*scale_mm_per_m), stroke="#caa9ff", sw=1.2, dash="6 4"))
    ln.append(_text(ox+body_w+12, Y(z)+14, "INSTRUMENT UNIT",12,"#caa9ff"))
    z+=L_IU + GAP

    # S-IVB (3단) — LH2 큰 탱크 + LOX 작은 탱크 + J-2 (1기)
    h4=L_SIVB
    ln.append(_box(ox, Y(z), body_w, int(h4*scale_mm_per_m), stroke="#ffffff", sw=1.6))
    # 내부 탱크
    h4_lox = 4.5; h4_lh2 = h4 - h4_lox - 1.2
    ln.append(_box(ox+6, Y(z)+6, body_w-12, int(h4_lox*scale_mm_per_m)-6, stroke="#9fd3ff", sw=1.4)) # LOX
    ln.append(_text(ox+10, Y(z)+18, "LOX",12,"#9fd3ff"))
    ln.append(_box(ox+6, Y(z)+int((h4_lox+0.8)*scale_mm_per_m), body_w-12, int(h4_lh2*scale_mm_per_m)-6, stroke="#ffd39f", sw=1.4)) # LH2
    ln.append(_text(ox+10, Y(z)+int((h4_lox+0.8)*scale_mm_per_m)+16, "LH2",12,"#ffd39f"))
    # J-2 (1기)
    eg_y = Y(z+h4)-18
    ln.append(_tri(ox+body_w*0.5, eg_y, 28, 30))
    ln.append(_text(ox+body_w+12, Y(z)+int(h4*scale_mm_per_m*0.5), "S-IVB — J-2 x1",12,"#9cd0ff"))
    z+=h4 + GAP

    # S-II(2단) — LOX 위, LH2 아래, J-2 x5
    h2=L_SII
    ln.append(_box(ox, Y(z), body_w, int(h2*scale_mm_per_m), stroke="#ffffff", sw=1.6))
    ln.append(_box(ox+6, Y(z)+6, body_w-12, int((h2*0.35)*scale_mm_per_m)-8, stroke="#9fd3ff", sw=1.4))  # LOX
    ln.append(_text(ox+10, Y(z)+18, "LOX",12,"#9fd3ff"))
    ln.append(_box(ox+6, Y(z)+int((h2*0.35+0.6)*scale_mm_per_m), body_w-12, int((h2*0.60)*scale_mm_per_m)-8, stroke="#ffd39f", sw=1.4)) # LH2
    ln.append(_text(ox+10, Y(z)+int((h2*0.35+0.6)*scale_mm_per_m)+16, "LH2",12,"#ffd39f"))
    # 엔진 5기
    base = Y(z+h2)-20
    for k in range(5):
        cx = ox+body_w*(0.2+0.15*k)
        ln.append(_tri(cx, base, 24, 26))
    ln.append(_text(ox+body_w+12, Y(z)+int(h2*scale_mm_per_m*0.5), "S-II — J-2 x5",12,"#9cd0ff"))
    z+=h2 + GAP

    # S-IC(1단) — LOX 위 / RP-1 아래 / F-1 x5
    h1=L_SIC
    ln.append(_box(ox, Y(z), body_w, int(h1*scale_mm_per_m), stroke="#ffffff", sw=1.8))
    # 상부 LOX
    ln.append(_box(ox+6, Y(z)+6, body_w-12, int((h1*0.42)*scale_mm_per_m)-8, stroke="#9fd3ff", sw=1.6))
    ln.append(_text(ox+10, Y(z)+18, "LOX",12,"#9fd3ff"))
    # 인터탱크 (점선)
    it_y0 = Y(z)+int((h1*0.42)*scale_mm_per_m)
    ln.append(_box(ox+4, it_y0, body_w-8, int(0.9*scale_mm_per_m), stroke="#89ffa8", sw=1.2, dash="8 4"))
    ln.append(_text(ox+body_w+12, it_y0+12, "INTERTANK",12,"#89ffa8"))
    # 하부 RP-1
    ln.append(_box(ox+6, it_y0+int(0.9*scale_mm_per_m), body_w-12, int((h1*0.55)*scale_mm_per_m)-12, stroke="#ffd39f", sw=1.6))
    ln.append(_text(ox+10, it_y0+int(0.9*scale_mm_per_m)+16, "RP-1",12,"#ffd39f"))
    # F-1 x5
    base = Y(z+h1)-22
    for k in range(5):
        cx = ox+body_w*(0.15+0.17*k)
        ln.append(_tri(cx, base, 26, 28))
    ln.append(_text(ox+body_w+12, Y(z)+int(h1*scale_mm_per_m*0.5), "S-IC — F-1 x5",12,"#9cd0ff"))

    # 좌측 치수선
    ln.append(_dim_v(ox-20, Y(0), Y(L_IU), f"IU {L_IU:.1f} m"))
    ln.append(_dim_v(ox-40, Y(L_IU+GAP), Y(L_IU+GAP+L_SIVB), f"S-IVB {L_SIVB:.1f} m"))
    ln.append(_dim_v(ox-60, Y(L_IU+GAP+L_SIVB+GAP), Y(L_IU+GAP+L_SIVB+GAP+L_SII), f"S-II {L_SII:.1f} m"))
    ln.append(_dim_v(ox-80, Y(L_IU+GAP+L_SIVB+GAP+L_SII+GAP), Y(L_IU+GAP+L_SIVB+GAP+L_SII+GAP+L_SIC), f"S-IC {L_SIC:.1f} m"))
    # 하단 직경
    ln.append(_dim_h(ox, ox+body_w, Y(L_IU+L_SIVB+L_SII+L_SIC+3*GAP)+40, f"D ≈ {D_stack:.2f} m  (scale {scale_mm_per_m:.1f} mm/m)"))

    # 범례
    ln.append(_legend(W-290, 28, [
        ("LOX tank", "#9fd3ff"),
        ("LH2 / RP-1 tank", "#ffd39f"),
        ("Intertank / interstage", "#89ffa8"),
        ("Engine schematics", "#9cd0ff"),
    ]))

    # 타이틀
    ln.append(_text(ox, 36, "SATURN V — VERTICAL STACK (Educational Blueprint)", 14, "#ffffff"))
    ln.append("</svg>")

    svg = "\n".join(ln)
    os.makedirs(out_dir, exist_ok=True)
    out_svg = os.path.join(out_dir, "saturn_stack.svg")
    open(out_svg,"w",encoding="utf-8").write(svg)
    return out_svg

def _safe(rel:str):
    base=os.path.abspath("data")
    full=os.path.abspath(os.path.join(base,rel.replace("/",os.sep)))
    return full if full.startswith(base) else None

@api.get("/cad/saturn_stack_blueprint")
def saturn_stack_blueprint(scale: float = Query(10.0, ge=4.0, le=24.0)):
    run = "run-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(RUNS_DIR, run)
    svg = _emit_stack_svg(out_dir, scale_mm_per_m=scale)
    rel = os.path.relpath(svg, start=os.path.abspath("data")).replace("\\","/")
    meta = {"ok": True, "svg_rel": rel, "run_dir": out_dir, "scale": scale}
    open(os.path.join(out_dir,"meta.json"),"w",encoding="utf-8").write(json.dumps(meta,indent=2))
    open(os.path.join(RUNS_DIR,"_last.json"),"w",encoding="utf-8").write(json.dumps(meta,indent=2))
    return meta

# 구버전 호환(있을 수 있는 호출)
@api.get("/cad/saturn_s1c_blueprint")
def saturn_s1c_blueprint(scale: float = Query(10.0, ge=4.0, le=24.0)):
    return saturn_stack_blueprint(scale=scale)

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    full=_safe(rel_path)
    if not full or not os.path.exists(full):
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
