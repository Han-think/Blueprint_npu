from __future__ import annotations
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
import os, json, math, datetime

RUNS_DIR=os.path.join("data","geometry","cad","j58_v23_runs")
api=APIRouter(prefix="/wb")

def _latest(d):
    if not os.path.isdir(d): return None
    s=[x for x in sorted(os.listdir(d)) if x.startswith("run-")]
    return os.path.join(d,s[-1]) if s else None

def _load_meta(out_dir:str|None):
    for r in [out_dir,_latest(RUNS_DIR)]:
        if not r: continue
        p=os.path.join(r,"j58_v23_bom.json")
        if os.path.exists(p): return json.load(open(p,encoding="utf-8")), r
    return None, None

# --- tiny svg helpers ---
def L(x): return int(x)
def _line(x0,y0,x1,y1,cls="s"): return f"<line x1='{L(x0)}' y1='{L(y0)}' x2='{L(x1)}' y2='{L(y1)}' class='{cls}'/>"
def _rect(x,y,w,h,cls="s"): return f"<rect x='{L(x)}' y='{L(y)}' width='{L(w)}' height='{L(h)}' class='{cls}'/>"
def _text(x,y,t,cls="t",anc="start"): return f"<text x='{L(x)}' y='{L(y)}' class='{cls}' text-anchor='{anc}'>{t}</text>"
def _circ(cx,cy,r,cls="s"): return f"<circle cx='{L(cx)}' cy='{L(cy)}' r='{L(r)}' class='{cls}'/>"

# --- sections (discs) ---
def _section_disc(cx,cy,R,hub,rotor,stator,label):
    g=[f"<g><rect x='{cx-160}' y='{cy-120}' width='320' height='240' class='s'/>",
       f"<text x='{cx-148}' y='{cy-96}' class='tb'>{label}</text>",
       _circ(cx,cy,R), _circ(cx,cy,hub)]
    # rotor blades
    for k in range(max(3,int(rotor))):
        th=2*math.pi*k/max(3,int(rotor))
        x0=cx+hub*math.cos(th); y0=cy+hub*math.sin(th)
        x1=cx+(R-10)*math.cos(th); y1=cy+(R-10)*math.sin(th)
        g.append(_line(x0,y0,x1,y1))
    # stator ring (short ticks)
    for k in range(max(3,int(stator))):
        th=2*math.pi*(k+0.5)/max(3,int(stator))
        x0=cx+(hub+14)*math.cos(th); y0=cy+(hub+14)*math.sin(th)
        x1=cx+(hub+34)*math.cos(th); y1=cy+(hub+34)*math.sin(th)
        g.append(_line(x0,y0,x1,y1,"dim"))
    g.append("</g>")
    return "\n".join(g)

# --- longitudinal bands helpers ---
def _ticks_band(x0,x1,y_top,y_bot,n,alt=False):
    seg=[]; n=max(1,int(n))
    step=(x1-x0)/(n*2)
    for i in range(n*2):
        x=x0+i*step
        y0=y_top+(i%2)*6*(1 if not alt else -1)
        y1=y_bot-(i%2)*6*(1 if not alt else -1)
        seg.append(_line(x,y0,x,y1))
    return "\n".join(seg)

def _chevrons(x0,x1,yc,h,step=16):
    g=[]; x=x0
    while x<x1:
        g.append(_line(x,yc-h,x+h,yc, "dim"))
        g.append(_line(x+2,yc+h,x+h+2,yc, "dim"))
        x+=step
    return "\n".join(g)

def _emit_svg(meta:dict, out_dir:str)->str:
    p=meta["params"]
    Ltot=float(p["L_total"]); R=float(p["R_casing"]); eps=float(p["eps"])
    Nf=int(p.get("N_fan",12)); Nc=int(p.get("N_comp",14)); Nt=int(p.get("N_turb",16))
    drive_z_frac=float(p.get("drive_z_frac",0.18)); engine_cc=float(p.get("engine_cc",120.0))

    # segment lengths
    Lin=0.12*Ltot; Lfan=0.10*Ltot; Lcomp1=0.10*Ltot; Lcomp2=0.08*Ltot
    Lcomb=0.20*Ltot; Ltur1=0.06*Ltot; Ltur2=0.06*Ltot; Lab=0.12*Ltot
    Lnoz=min(0.16*Ltot,0.18*Ltot)
    z_fan=Lin+Lfan
    z_comp1=z_fan+Lcomp1
    z_comp2=z_comp1+Lcomp2
    z_comb=z_comp2+Lcomb
    z_turb1=z_comb+Ltur1
    z_turb2=z_turb1+Ltur2
    z_ab=z_turb2+Lab
    r_th=0.35*R; r_ex=min(math.sqrt(max(1e-9, eps*math.pi*(r_th**2))/math.pi), 0.97*R-0.15)

    # canvas
    sx=2.6; sy=2.6
    pad=120; side_gap=160; panel_gap=110
    W=int(Ltot*sx)+pad*2+380+side_gap
    H=max(int(4.8*R*sy)+pad*2, pad+4*240+3*panel_gap+pad)
    ox,oy=pad,H//2
    X=lambda zz: ox+zz*sx
    Y=lambda rr: oy-rr*sy

    # body outline
    pts=[]; z=0.0
    def seg_cyl(len_,r):
        nonlocal z; pts.append((X(z),Y(r))); z+=len_; pts.append((X(z),Y(r)))
    def seg_cone(len_,r0,r1):
        nonlocal z
        n=14
        for i in range(n+1):
            t=i/n; zz=z+len_*t; rr=r0+(r1-r0)*t; pts.append((X(zz),Y(rr)))
        z+=len_
    seg_cone(Lin, 0.34*R, 0.12*R)
    seg_cyl(Lfan+Lcomp1+Lcomp2, 0.98*R)
    seg_cyl(Lcomb, 0.95*R)
    seg_cyl(Ltur1+Ltur2+Lab, 0.98*R)
    seg_cone(Lnoz, r_th, r_ex)

    # svg header
    ln=[]
    ln.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    ln.append("""
<style>
.bg{fill:#153a68}
.frame{fill:none;stroke:#0b2340;stroke-width:2}
.s{stroke:#e6f0ff;stroke-width:1.6;fill:none}
.dim{stroke:#e6f0ff;stroke-width:1}
.dash{stroke-dasharray:6 4}
.t{fill:#e6f0ff;font:12px/1 system-ui}
.tb{fill:#e6f0ff;font:14px/1.2 system-ui;font-weight:600}
.hatch{fill:url(#h1);stroke:#e6f0ff;stroke-width:1}
.hatch2{fill:url(#h2);stroke:#e6f0ff;stroke-width:1}
.legend{fill:#0f2f55;stroke:#e6f0ff;stroke-width:1}
</style>
<defs>
 <pattern id='h1' width='8' height='8' patternUnits='userSpaceOnUse' patternTransform='rotate(60)'>
   <line x1='0' y1='0' x2='0' y2='8' stroke='#9fd3ff' stroke-width='1'/>
 </pattern>
 <pattern id='h2' width='8' height='8' patternUnits='userSpaceOnUse' patternTransform='rotate(120)'>
   <line x1='0' y1='0' x2='0' y2='8' stroke='#9fd3ff' stroke-width='1'/>
 </pattern>
 <marker id='arrow' viewBox='0 0 10 10' refX='10' refY='5' markerUnits='strokeWidth' markerWidth='8' markerHeight='6' orient='auto'>
   <path d='M 0 0 L 10 5 L 0 10 z' fill='#e6f0ff'/>
 </marker>
</defs>
""")
    ln.append("<rect class='bg' width='100%' height='100%'/>")
    ln.append(f"<rect class='frame' x='12' y='12' width='{W-24}' height='{H-24}'/>")
    ln.append(_line(X(0),oy,X(Ltot),oy,"s dash"))

    # outline
    path_top=" ".join([f'L {L(x)} {L(y)}' for x,y in pts[1:]])
    path_bot=" ".join([f'L {L(x)} {L(2*oy-y)}' for x,y in pts[1:][::-1]])
    ln.append(f"<path d='M {L(pts[0][0])} {L(pts[0][1])} {path_top} {path_bot} Z' class='s'/>")

    # labels & bands
    yTop=Y(0.90*R); yBot=Y(-0.90*R)
    # inlet: spike + shock-bleed/bypass doors
    ln.append(_text(X(0)+6, Y(0.98*R)-10, "INLET / SPIKE"))
    ln.append(_line(X(0.05*Lin), oy-18, X(0.28*Lin), oy-34, "dim"))
    ln.append(_text(X(0.28*Lin)+6, oy-36, "SHOCK TRAP BLEED →", anc="start"))
    ln.append(_rect(X(0.70*Lin), Y(0.60*R), 24, 22, "dim"))
    ln.append(_text(X(0.70*Lin)+28, Y(0.60*R)+14, "FWD BYPASS DOOR", anc="start"))

    # fan (rotor/stator alt ticks)
    ln.append(_text(X(Lin)+6, Y(0.98*R)-10, "FAN"))
    ln.append(_ticks_band(X(Lin), X(Lin+Lfan*0.55), yTop, yBot, max(1,Nf//2), alt=False))
    ln.append(_ticks_band(X(Lin+Lfan*0.55), X(Lin+Lfan), yTop, yBot, max(1,Nf//2), alt=True))

    # compressor split 2
    ln.append(_text(X(z_fan)+6, Y(0.98*R)-10, "COMP-1"))
    ln.append(_ticks_band(X(z_fan), X(z_comp1), yTop, yBot, max(2,Nc//2), alt=False))
    ln.append(_text(X(z_comp1)+6, Y(0.98*R)-10, "COMP-2"))
    ln.append(_ticks_band(X(z_comp1), X(z_comp2), yTop, yBot, max(2,Nc//2), alt=True))

    # combustor/liner + flameholder (chevrons) + AB spray ring
    cx0=X(z_comp2); cx1=X(z_comb)
    ln.append(_text(cx0+6, Y(0.98*R)-10, "COMBUSTOR / LINER"))
    # outer/inner liner (double wall)
    ln.append(_rect(cx0, Y(0.70*R), (cx1-cx0), (Y(-0.70*R)-Y(0.70*R)), "s"))
    ln.append(_rect(cx0+10, Y(0.52*R), (cx1-cx0)-20, (Y(-0.52*R)-Y(0.52*R)), "s"))
    # service hatch (hatched panel)
    ln.append(_rect(cx0+18, Y(0.52*R), 44, (Y(-0.52*R)-Y(0.52*R)), "hatch2"))
    # flame holder chevrons
    ln.append(_chevrons(cx0+70, cx0+160, oy, 14))
    ln.append(_text(cx0+72, oy-18, "FLAME HOLDER", anc="start"))
    # afterburner spray ring (end of combustor)
    ln.append(_circ(cx1-26, oy, 10, "dim"))
    ln.append(_text(cx1-26, oy-16, "AB SPRAY RING", anc="middle"))

    # turbine 2 groups
    ln.append(_text(X(z_comb)+6, Y(0.98*R)-10, "TURB-1"))
    ln.append(_ticks_band(X(z_comb), X(z_turb1), yTop, yBot, max(2,Nt//2), alt=False))
    ln.append(_text(X(z_turb1)+6, Y(0.98*R)-10, "TURB-2"))
    ln.append(_ticks_band(X(z_turb1), X(z_turb2), yTop, yBot, max(2,Nt//2), alt=True))

    # AB case (hatched)
    ln.append(_rect(X(z_turb2), Y(0.80*R), X(z_ab)-X(z_turb2), Y(-0.80*R)-Y(0.80*R), "hatch"))
    ln.append(_text(X(z_turb2)+6, Y(0.80*R)-10, "A/B CASE"))

    # nozzle throat/exit
    throat_z=Ltot-Lnoz*0.60
    ln.append(_line(X(throat_z), oy-26, X(throat_z), oy+26))
    ln.append(_text(X(throat_z)+6, oy-30, "THROAT"))
    ln.append(_line(X(Ltot-Lnoz), oy-60, X(Ltot), oy-60, "dim"))
    ln.append(_line(X(Ltot-Lnoz), oy-66, X(Ltot-Lnoz), oy-54, "dim"))
    ln.append(_line(X(Ltot), oy-66, X(Ltot), oy-54, "dim"))
    ln.append(_text((X(Ltot-Lnoz)+X(Ltot))//2, oy-70, f"Nozzle L {Lnoz:.1f} mm", anc="middle"))
    ln.append(_text(X(Ltot)+56, oy-8, "EXHAUST"))
    ln.append(_line(X(Ltot)-10, oy, X(Ltot)+50, oy, "s"));  # arrow line
    # dimensions casing & eps
    ln.append(_text(X(0), Y(1.15*R), f"EPS {eps:.2f}", anc="start"))
    ln.append(_line(X(0)-44, oy, X(0)+12, oy, "s")); ln.append(_text(X(0)-50, oy-8, "INLET", anc="end"))

    # shaft + bearings + starter
    shaft_z0=max(0.09*Ltot, Lin*0.95); shaft_z1=Ltot-Lnoz*0.40
    ln.append(_line(X(shaft_z0), oy, X(shaft_z1), oy, "s"))
    for zz,lab in [(0.07*Ltot,"BEARING POCKET L"), (0.93*Ltot,"BEARING POCKET R")]:
        ln.append(_circ(X(zz), oy, 10, "s"))
        ln.append(_text(X(zz)+12, oy-6, lab, anc="start"))
    drive_z=drive_z_frac*Ltot
    ln.append(_rect(X(drive_z)-16, oy+40, 32, 20, "s"))
    ln.append(_text(X(drive_z), oy+36, "71 STARTER (130)", anc="middle"))
    ln.append(_line(X(drive_z), oy+40, X(drive_z), oy, "dim"))

    # side sections A/B/C + extra D/E/F
    px=X(Ltot)+side_gap; cy0=pad+120; gap=panel_gap+240
    ln.append(_section_disc(px+180, cy0,     84, 22, Nf, Nf, "SECTION A–A (FAN)"))
    ln.append(_section_disc(px+180, cy0+gap, 84, 22, Nc, Nc, "SECTION B–B (COMP)"))
    ln.append(_section_disc(px+180, cy0+2*gap, 84, 22, Nt, Nt, "SECTION C–C (TURBINE)"))
    # D: combustor annulus
    cx=px+180; cy=cy0+3*gap
    ln.append(f"<g><rect x='{cx-160}' y='{cy-120}' width='320' height='240' class='s'/>")
    ln.append(_text(cx-148, cy-96, "SECTION D–D (COMBUSTOR ANNULUS)", "tb"))
    ln.append(_circ(cx,cy,88)); ln.append(_circ(cx,cy,64)); ln.append(_circ(cx,cy,40))
    ln.append(_text(cx, cy+96, "outer | liner | core", anc="middle"))
    ln.append("</g>")
    # E: nozzle throat/exit rings
    cy=cy0+4*gap
    ln.append(f"<g><rect x='{cx-160}' y='{cy-120}' width='320' height='240' class='s'/>")
    ln.append(_text(cx-148, cy-96, "SECTION E–E (NOZZLE)", "tb"))
    ln.append(_circ(cx,cy, int(r_ex*sy*0.6)))
    ln.append(_circ(cx,cy, int(r_th*sy*0.6), "dim"))
    ln.append(_text(cx, cy+96, "exit (outer)  /  throat (dim)", anc="middle"))
    ln.append("</g>")
    # F: bearing pocket detail
    cy=cy0+5*gap
    ln.append(f"<g><rect x='{cx-160}' y='{cy-120}' width='320' height='240' class='s'/>")
    ln.append(_text(cx-148, cy-96, "SECTION F–F (BEARING POCKET)", "tb"))
    ln.append(_circ(cx,cy,60)); ln.append(_circ(cx,cy,36)); ln.append(_circ(cx,cy,12))
    ln.append(_text(cx, cy+96, "seat | race | shaft", anc="middle"))
    ln.append("</g>")

    # twin/starter inset (schematic)
    ix=X(0); iy=H-pad-140
    ln.append(_rect(ix, iy, 280, 110, "s"))
    ln.append(_text(ix+8, iy+20, "TWIN STARTER SCHEMATIC", "tb"))
    ln.append(_circ(ix+70,  iy+68, 28)); ln.append(_circ(ix+210, iy+68, 28))
    ln.append(_rect(ix+136, iy+58, 32, 20, "s"))
    ln.append(_line(ix+136, iy+68, ix+98,  iy+68))
    ln.append(_line(ix+168, iy+68, ix+182, iy+68))
    ln.append(_text(ix+152, iy+92, "MOTOR 130", anc="middle"))
    ln.append(_text(ix+70,  iy+100, "LEFT SHAFT", anc="middle"))
    ln.append(_text(ix+210, iy+100, "RIGHT SHAFT", anc="middle"))

    # title block + legend
    tbx=X(0); tby=H-pad-260; tbw=640; tbh=110
    ln.append(_rect(tbx, tby, tbw, tbh, "s"))
    ln.append(_text(tbx+12, tby+24, "J58 TWIN — INTERNAL MASTER BLUEPRINT", "tb"))
    ln.append(_text(tbx+12, tby+44, f"REV: H5  DATE: {datetime.date.today().isoformat()}"))
    ln.append(_text(tbx+12, tby+64, f"EPS {eps:.2f} | engine_cc {engine_cc:.1f} | drive_z {drive_z:.1f} mm"))
    ln.append(_text(tbx+12, tby+84, "Stages: inlet, fan (rotor/stator), compressor(2), combustor liner + flameholder + AB ring, turbine(2), AB case, nozzle."))

    lgx=tbx+tbw+18; lgy=tby
    ln.append(_rect(lgx, lgy, 260, tbh, "s"))
    ln.append(_text(lgx+10, lgy+24, "LEGEND", "tb"))
    ln.append(_rect(lgx+12, lgy+36, 18, 10, "hatch"));  ln.append(_text(lgx+38, lgy+44, "Afterburner case / hatch"))
    ln.append(_rect(lgx+12, lgy+56, 18, 10, "hatch2")); ln.append(_text(lgx+38, lgy+64, "Service hatch (combustor)"))
    ln.append(_line(lgx+12, lgy+76, lgx+30, lgy+76));    ln.append(_text(lgx+38, lgy+80, "Rotor/Stator tick bands"))
    ln.append(_circ(lgx+21, lgy+98, 5));                 ln.append(_text(lgx+38, lgy+102, "Bearing pocket / rings"))

    ln.append("</svg>")
    out=os.path.join(out_dir,"blueprint.svg")
    open(out,"w",encoding="utf-8").write("\n".join(ln))
    return out

@api.get("/cad/j58_blueprint")
def j58_blueprint(out_dir:str|None=Query(None)):
    meta, run = _load_meta(out_dir)
    if not meta: return JSONResponse({"ok":False,"reason":"no_run_found"}, status_code=404)
    svg=_emit_svg(meta, run)
    rel=os.path.relpath(svg, start=os.path.abspath("data")).replace("\\","/")
    return {"ok":True,"svg_rel":rel,"run_dir":run}

@api.get("/files/{rel_path:path}")
def send_file(rel_path:str):
    base=os.path.abspath("data"); full=os.path.abspath(os.path.join(base,rel_path.replace("/",os.sep)))
    if not full.startswith(base) or not os.path.exists(full):
        return JSONResponse({"ok":False,"reason":"not_found","rel":rel_path}, status_code=404)
    return FileResponse(full)
