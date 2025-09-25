from __future__ import annotations
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime

api = APIRouter(prefix="/wb", tags=["saturn"])
ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "data/geometry/cad/saturn_stack"
OUT.mkdir(parents=True, exist_ok=True)

def box(x,y,w,h,stroke="#fff",sw=1.6,fill="none",dash=None):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'{d}/>"
def text(x,y,t,fs=12,fill="#fff",anc="start"):
    return f"<text x='{x}' y='{y}' fill='{fill}' font-size='{fs}' text-anchor='{anc}'>{t}</text>"
def tank_capsule(x,y,w,h,r,stroke,fill="none",sw=1.3):
    return (f"<path d='M {x} {y+r} A {r} {r} 0 0 1 {x+r} {y} L {x+w-r} {y} "
            f"A {r} {r} 0 0 1 {x+w} {y+r} L {x+w} {y+h-r} A {r} {r} 0 0 1 {x+w-r} {y+h} "
            f"L {x+r} {y+h} A {r} {r} 0 0 1 {x} {y+h-r} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
def tri(cx,cy,w,h,stroke="#9cd0ff",fill="#1f6aa8",sw=1):
    x1,y1=cx,cy-h/2; x2,y2=cx-w/2,cy+h/2; x3,y3=cx+w/2,cy+h/2
    return f"<path d='M {x1} {y1} L {x2} {y2} L {x3} {y3} Z' fill='{fill}' stroke='{stroke}' stroke-width='{sw}' opacity='0.9'/>"

@api.get("/cad/saturn_overview_h")
def saturn_overview_h(scale: float = Query(12.0, ge=4.0, le=24.0)):
    try:
        L1,L2,L3 = 42.1, 24.9, 17.8
        D33, D21 = 10.1, 6.60
        mm        = scale
        pad_left  = 40
        pad_top   = 70
        gap       = 88
        foot_pad  = 120
        maxL      = max(L1,L2,L3)
        w33 = D33*mm; w21 = D21*mm
        W   = int(pad_left*2 + w33 + gap + w33 + gap + w21 + 260)
        H   = int(pad_top + maxL*mm + foot_pad)
        baseY = int(pad_top + maxL*mm)

        svg=[f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
             "<rect width='100%' height='100%' fill='#0c1e35'/>",
             f"<rect x='8' y='8' width='{W-16}' height='{H-16}' fill='none' stroke='#274a79' stroke-width='2'/>",
             text(24,28,'SATURN V — Horizontal Stage Overview (1→2→3)',14,'#fff'),
             text(24,46,f'Scale {scale:.1f} mm/m',11,'#9fd3ff'),
             f"<line x1='{pad_left-6}' y1='{baseY}' x2='{W-12}' y2='{baseY}' stroke='#cfd6e6' stroke-width='1'/>"
        ]

        def stage(x, L, D, title, eng_notes, is_s4b=False):
            w = (w21 if is_s4b else w33) if not is_s4b else w21
            if not is_s4b and D != 10.1:
                w = D*mm
            h = L*mm
            top = baseY - h
            svg.append(box(x, top, w, h, stroke="#fff", sw=1.6))

            if not is_s4b and title.startswith("S-IC"):
                lox = L*0.42; inter=0.9; rp1=L-lox-inter
                svg.extend([
                    tank_capsule(x+6, top+6, w-12, lox*mm-6, 26, "#9fd3ff"),
                    box(x+4, top+lox*mm, w-8, inter*mm, stroke="#89ffa8", sw=1.2, dash="8 4"),
                    tank_capsule(x+6, top+lox*mm+inter*mm, w-12, rp1*mm-12, 28, "#ffd39f")
                ])
                by = baseY + 18
                for dx in (-w*0.35,-w*0.175,0,w*0.175,w*0.35): svg.append(tri(x+w/2+dx, by, 18, 20))
                svg.append(text(x+w/2, by+22, eng_notes, 11, "#9cd0ff", "middle"))
            elif not is_s4b and title.startswith("S-II"):
                lox = L*0.22; lh2=L*0.73
                svg.extend([
                    tank_capsule(x+6, top+6, w-12, lox*mm-6, 22, "#9fd3ff"),
                    f"<polygon points='{x+10},{top+lox*mm+3} {x+w-10},{top+lox*mm+3} {x+w/2},{top+lox*mm+22}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>",
                    tank_capsule(x+6, top+lox*mm+22, w-12, lh2*mm-28, 24, "#b6ffb6")
                ])
                by = baseY + 18
                for dx in (-w*0.28,-w*0.14,0,w*0.14,w*0.28): svg.append(tri(x+w/2+dx, by, 16, 18))
                svg.append(text(x+w/2, by+22, eng_notes, 11, "#9cd0ff", "middle"))
            else:
                lox= L*0.26; lh2=L*0.69
                svg.extend([
                    tank_capsule(x+6, top+6, w-12, lox*mm-6, 18, "#9fd3ff"),
                    f"<polygon points='{x+9},{top+lox*mm+3} {x+w-9},{top+lox*mm+3} {x+w/2},{top+lox*mm+18}' fill='none' stroke='#89ffa8' stroke-width='1.2'/>",
                    tank_capsule(x+6, top+lox*mm+18, w-12, lh2*mm-24, 20, "#b6ffb6")
                ])
                by = baseY + 18
                svg.append(tri(x+w/2, by, 16, 18))
                svg.append(text(x+w/2, by+22, eng_notes, 11, "#9cd0ff", "middle"))

            svg.append(text(x+w/2, baseY + 44, title, 12, "#9fd3ff", "middle"))
            return x+w

        x = pad_left
        x  = stage(x, L1, D33, "S-IC (1단, Ø33 ft)",  "F-1 ×5"); x += gap
        x  = stage(x, L2, D33, "S-II (2단, Ø33 ft)",  "J-2 ×5");  x += gap
        x  = stage(x, L3, D21, "S-IVB (3단, Ø21.7 ft)","J-2 ×1", is_s4b=True)

        svg.extend([
            box(W-230,24,206,74,stroke="#fff",sw=1),
            box(W-216,36,16,10,stroke="#9fd3ff",sw=2), text(W-194,46,"LOX tank/line",11,"#9fd3ff"),
            box(W-216,54,16,10,stroke="#b6ffb6",sw=2), text(W-194,64,"LH2 tank",11,"#b6ffb6"),
            box(W-216,72,16,10,stroke="#ffd39f",sw=2), text(W-194,82,"RP-1 tank",11,"#ffd39f"),
            "</svg>"
        ])

        out = OUT / f"overview_h_{datetime.now():%Y%m%d-%H%M%S}.svg"
        out.write_text("\n".join(svg), encoding="utf-8")
        rel = str(out.relative_to(ROOT/"data")).replace("\\","/")
        return {"ok":True,"svg_rel":rel}
    except Exception as e:
        return JSONResponse({"ok":False,"reason":"render_error","msg":str(e)}, status_code=500)
