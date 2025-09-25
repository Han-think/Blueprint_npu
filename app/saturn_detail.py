from __future__ import annotations
from fastapi import APIRouter, Query
from pathlib import Path
from datetime import datetime

api = APIRouter(prefix="/wb", tags=["saturn"])

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "data/geometry/cad/saturn_stack"
OUT.mkdir(parents=True, exist_ok=True)

# ------- SVG helpers -------
def box(x,y,w,h,stroke="#fff",sw=1.6,fill="none",dash=None):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'{d}/>"

def text(x,y,t,fs=12,fill="#fff",anc="start"):
    return f"<text x='{x}' y='{y}' fill='{fill}' font-size='{fs}' text-anchor='{anc}'>{t}</text>"

def tri(cx,cy,w,h,stroke="#9cd0ff",fill="#1f6aa8",sw=1):
    x1,y1=cx,cy-h/2; x2,y2=cx-w/2,cy+h/2; x3,y3=cx+w/2,cy+h/2
    return f"<path d='M {x1} {y1} L {x2} {y2} L {x3} {y3} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' opacity='0.9'/>"

def dim_h(x0,x1,y,label):
    return "\n".join([
      f"<line x1='{x0}' y1='{y}' x2='{x1}' y2='{y}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x0}' y1='{y-6}' x2='{x0}' y2='{y+6}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x1}' y1='{y-6}' x2='{x1}' y2='{y+6}' stroke='white' stroke-width='1'/>",
      f"<text x='{(x0+x1)//2}' y='{y-8}' fill='white' font-size='12' text-anchor='middle'>{label}</text>"
    ])

def dim_v(x,y0,y1,label):
    return "\n".join([
      f"<line x1='{x}' y1='{y0}' x2='{x}' y2='{y1}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x-6}' y1='{y0}' x2='{x+6}' y2='{y0}' stroke='white' stroke-width='1'/>",
      f"<line x1='{x-6}' y1='{y1}' x2='{x+6}' y2='{y1}' stroke='white' stroke-width='1'/>",
      f"<text x='{x-8}' y='{(y0+y1)//2}' fill='white' font-size='12' text-anchor='end' dominant-baseline='middle'>{label}</text>"
    ])

def tank_capsule(x,y,w,h,r,stroke,fill="none",sw=1.3):
    # 상하 반원 + 직선(탱크 단면 시각화)
    return (
        f"<path d='M {x} {y+r} A {r} {r} 0 0 1 {x+r} {y} L {x+w-r} {y} "
        f"A {r} {r} 0 0 1 {x+w} {y+r} L {x+w} {y+h-r} A {r} {r} 0 0 1 {x+w-r} {y+h} "
        f"L {x+r} {y+h} A {r} {r} 0 0 1 {x} {y+h-r} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"
    )

def feedline(x0,y0,x1,y1,color="#9fd3ff"):
    return f"<path d='M {x0} {y0} C {x0+20} {y0} {x1-20} {y1} {x1} {y1}' stroke='{color}' stroke-width='2' fill='none'/>"

def legend(x,y,items):
    ln=[box(x,y,220,18*len(items)+14,stroke='#fff',sw=1,fill='none')]
    yy=y+16
    for label,color in items:
        ln.append(box(x+10,yy-10,18,12,stroke=color,sw=2))
        ln.append(text(x+36,yy,label,12,"#fff"))
        yy+=18
    return "\n".join(ln)

# ------- API -------
@api.get("/cad/saturn_stack_detail")
def saturn_stack_detail(
    scale: float = Query(10.0, ge=4.0, le=24.0),
    show_plumbing: bool = True,
    show_sep_motors: bool = True,
    show_interstages: bool = True
):
    # 근사 교육용 스펙(비율 우선)
    D_33    = 10.1   # m (S-IC, S-II)
    D_21_7  = 6.60   # m (S-IVB)
    L_SIC   = 42.1
    L_SII   = 24.9
    L_SIVB  = 17.8
    L_IU    = 0.9
    GAP     = 1.3

    W = 980
    H = int((L_IU+L_SIVB+L_SII+L_SIC+3*GAP)*scale + 170)
    ox, oy = 220, 70
    body_w = int(D_33*scale)

    def Y(zm): return oy + int(zm*scale)

    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("<rect width='100%' height='100%' fill='#0c1e35'/>")
    ln.append(box(16,16,W-32,H-32,stroke='#274a79',sw=2))
    ln.append(text(28,40,"SATURN V — Vertical Stack (Detailed Educational Blueprint)",14,"#fff"))
    ln.append(text(28,58,f"Scale {scale:.1f} mm/m",11,"#9fd3ff"))

    z=0.0
    # IU
    ln.append(box(ox, Y(z), body_w, int(L_IU*scale), stroke="#caa9ff", sw=1.2, dash="6 4"))
    ln.append(text(ox+body_w+12, Y(z)+14, "INSTRUMENT UNIT",12,"#caa9ff"))
    z+=L_IU + GAP

    # S-IVB
    h4=L_SIVB
    w4=int(D_21_7*scale); x4=ox+(body_w-w4)//2
    ln.append(box(x4, Y(z), w4, int(h4*scale), stroke="#fff", sw=1.6))
    lox4 = h4*0.26; lh2_4 = h4*0.69
    ln.append(tank_capsule(x4+6, Y(z)+6, w4-12, lox4*scale-6, 16, "#9fd3ff"))
    ln.append(text(x4-10, Y(z)+16, "LOX", "#9fd3ff", 11, "end"))
    ln.append(f"<polygon points='{x4+10},{Y(z+lox4)+3} {x4+w4-10},{Y(z+lox4)+3} {(x4+x4+w4)//2},{Y(z+lox4)+18}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>")
    ln.append(tank_capsule(x4+6, Y(z+lox4)+18, w4-12, lh2_4*scale-24, 18, "#b6ffb6"))
    ln.append(text(x4+w4+10, Y(z+lox4+lh2_4)-6, "LH2", "#b6ffb6", 11, "start"))
    # J-2 x1
    eg_y = Y(z+h4)+18
    ln.append(tri(x4+w4/2, eg_y, 22, 24))
    ln.append(text(x4+w4/2, eg_y+24, "J-2 x1", 11, "#9cd0ff", "middle"))
    if show_interstages:
        ln.append(box(ox, Y(z+h4), body_w, int(GAP*scale*0.7), stroke="#89ffa8", sw=1.2, dash="8 4"))
        ln.append(text(ox+body_w+12, Y(z+h4)+12, "INTERSTAGE (S-IVB/S-II)",11,"#89ffa8"))
    if show_sep_motors:
        ln.append(tri(ox-20, Y(z+h4)+10, 10, 12, fill="#aa8844", stroke="#ffd39f"))
        ln.append(tri(ox+body_w+20, Y(z+h4)+10, 10, 12, fill="#aa8844", stroke="#ffd39f"))
    z+=h4 + GAP

    # S-II
    h2=L_SII
    ln.append(box(ox, Y(z), body_w, int(h2*scale), stroke="#fff", sw=1.6))
    lox2 = h2*0.22; lh2_2 = h2*0.73
    ln.append(tank_capsule(ox+6, Y(z)+6, body_w-12, lox2*scale-6, 22, "#9fd3ff"))
    ln.append(text(ox-10, Y(z)+16, "LOX (common bulkhead)", "#9fd3ff", 11, "end"))
    ln.append(f"<polygon points='{ox+10},{Y(z+lox2)+3} {ox+body_w-10},{Y(z+lox2)+3} {ox+body_w/2},{Y(z+lox2)+24}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>")
    ln.append(tank_capsule(ox+6, Y(z+lox2)+24, body_w-12, lh2_2*scale-30, 24, "#b6ffb6"))
    ln.append(text(ox+body_w+12, Y(z+lox2+lh2_2)-6, "LH2", "#b6ffb6", 11, "start"))
    # J-2 x5
    base = Y(z+h2)+18
    for dx in (-80,-40,0,40,80):
        ln.append(tri(ox+body_w/2+dx, base, 20, 22))
    ln.append(text(ox+body_w/2, base+22, "J-2 x5", 11, "#9cd0ff", "middle"))
    if show_interstages:
        ln.append(box(ox, Y(z+h2), body_w, int(GAP*scale*0.7), stroke="#89ffa8", sw=1.2, dash="8 4"))
        ln.append(text(ox+body_w+12, Y(z+h2)+12, "INTERSTAGE (S-II/S-IC)",11,"#89ffa8"))
    if show_sep_motors:
        ln.append(tri(ox-20, Y(z+h2)+10, 10, 12, fill="#aa8844", stroke="#ffd39f"))
        ln.append(tri(ox+body_w+20, Y(z+h2)+10, 10, 12, fill="#aa8844", stroke="#ffd39f"))
    z+=h2 + GAP

    # S-IC
    h1=L_SIC
    ln.append(box(ox, Y(z), body_w, int(h1*scale), stroke="#fff", sw=1.8))
    lox1 = h1*0.42; inter_h=0.9; rp1 = h1 - lox1 - inter_h
    ln.append(tank_capsule(ox+6, Y(z)+6, body_w-12, lox1*scale-6, 26, "#9fd3ff"))
    ln.append(text(ox-10, Y(z)+16, "LOX", "#9fd3ff", 11, "end"))
    it_y0 = Y(z+lox1)
    ln.append(box(ox+4, it_y0, body_w-8, int(inter_h*scale), stroke="#89ffa8", sw=1.2, dash="8 4"))
    ln.append(text(ox+body_w+12, it_y0+14, "INTERTANK", 11, "#89ffa8"))
    ln.append(tank_capsule(ox+6, it_y0+int(inter_h*scale), body_w-12, rp1*scale-12, 28, "#ffd39f"))
    ln.append(text(ox-10, it_y0+int(inter_h*scale)+16, "RP-1", "#ffd39f", 11, "end"))
    # F-1 x5
    base = Y(z+h1)+20
    for dx in (-100,-50,0,50,100):
        ln.append(tri(ox+body_w/2+dx, base, 24, 26))
    ln.append(text(ox+body_w/2, base+24, "F-1 x5", 11, "#9cd0ff", "middle"))

    # 배관(단순화)
    if show_plumbing:
        # S-IC: LOX feedline 상부→하부
        ln.append(feedline(ox+body_w-8, Y(z)+20, ox+body_w-8, base-40, "#9fd3ff"))
        # RP-1 배출 라인
        ln.append(feedline(ox+8, it_y0+int(inter_h*scale)+20, ox+8, base-36, "#ffd39f"))
        # S-II/S-IVB LOX/LH2 간단 루트
        ln.append(feedline(ox+body_w-6, Y(z - GAP - L_SII + 2), ox+body_w-6, Y(z - GAP) - 6, "#9fd3ff"))
        ln.append(feedline(ox+6, Y(z - GAP - L_SII + L_SII*0.5), ox+6, Y(z - GAP) + 12, "#b6ffb6"))

    # 좌/하 치수
    ln.append(dim_v(ox-24, Y(0), Y(L_IU), f"IU {L_IU:.1f} m"))
    ln.append(dim_v(ox-44, Y(L_IU+GAP), Y(L_IU+GAP+L_SIVB), f"S-IVB {L_SIVB:.1f} m"))
    ln.append(dim_v(ox-64, Y(L_IU+GAP+L_SIVB+GAP), Y(L_IU+GAP+L_SIVB+GAP+L_SII), f"S-II {L_SII:.1f} m"))
    ln.append(dim_v(ox-84, Y(L_IU+GAP+L_SIVB+GAP+L_SII+GAP), Y(L_IU+GAP+L_SIVB+GAP+L_SII+GAP+L_SIC), f"S-IC {L_SIC:.1f} m"))
    ln.append(dim_h(ox, ox+body_w, Y(L_IU+L_SIVB+L_SII+L_SIC+3*GAP)+44, f"D (S-IC/S-II) ≈ {D_33:.2f} m"))

    # 범례
    ln.append(legend(W-260, 24, [
        ("LOX tank / line", "#9fd3ff"),
        ("LH2 / RP-1 tank", "#b6ffb6"),
        ("Intertank/Interstage", "#89ffa8"),
        ("Engine schematic", "#9cd0ff"),
    ]))

    ln.append("</svg>")

    out = OUT / f"saturn_stack_detail_{datetime.now():%Y%m%d-%H%M%S}.svg"
    out.write_text("\n".join(ln), encoding="utf-8")
    rel = str(out.relative_to(ROOT)).replace("\\","/")
    return {"ok": True, "svg_rel": rel}
