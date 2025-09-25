# app/j58_sprue.py
from __future__ import annotations
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import numpy as np, trimesh as tm
import os, json, datetime
from typing import List, Tuple

# v23(신규) 우선, 없으면 구버전(j58_runs)
RUNS_V23 = os.path.join("data", "geometry", "cad", "j58_v23_runs")
RUNS_OLD = os.path.join("data", "geometry", "cad", "j58_runs")
os.makedirs(RUNS_V23, exist_ok=True)

# ---------- 공용 유틸 ----------
def _safe(rel: str) -> str | None:
    base = os.path.abspath("data")
    p = os.path.abspath(os.path.join(base, rel.replace("/", os.sep)))
    return p if p.startswith(base) else None

def _latest(dir_: str) -> str | None:
    if not os.path.isdir(dir_): return None
    runs = [d for d in sorted(os.listdir(dir_)) if d.startswith("run-")]
    return os.path.join(dir_, runs[-1]) if runs else None

def _load_meta(out_dir: str | None) -> tuple[dict | None, str | None, str | None]:
    cand: List[str | None] = []
    if out_dir: cand.append(out_dir)
    cand += [_latest(RUNS_V23), _latest(RUNS_OLD)]
    for r in cand:
        if not r: continue
        p1 = os.path.join(r, "j58_v23_bom.json")
        p2 = os.path.join(r, "j58_bom.json")
        if os.path.exists(p1): return json.load(open(p1, encoding="utf-8")), r, "v23"
        if os.path.exists(p2): return json.load(open(p2, encoding="utf-8")), r, "old"
    return None, None, None

def load_mesh(path: str) -> tm.Trimesh:
    m = tm.load(path) if path.lower().endswith(".stl") else tm.load_mesh(path)
    return m if isinstance(m, tm.Trimesh) else tm.util.concatenate(m.dump())

def rect_plate(w: float, d: float, t: float = 2.0) -> tm.Trimesh:
    m = tm.creation.box(extents=[w, d, t])
    m.apply_translation([w * 0.5, d * 0.5, t * 0.5])
    return m

# ---------- 파트 선택(코어 / 쉘 / 전체) ----------
CORE_KEYS = [
    ("fan_rotor", "fan_rotor"),
    ("fan_stator", "fan_stator"),
    ("comp_rotor", "compressor_rotor"),
    ("comp_stator", "compressor_stator"),
    ("turb_rotor", "turbine_rotor"),
    ("turb_stator", "turbine_stator"),
    ("seat_fan", "seat_fan"),
    ("seat_comp", "seat_comp"),
    ("seat_turb", "seat_turb"),
    ("bearing_holder_L", "bearing_holder_L"),
    ("bearing_holder_R", "bearing_holder_R"),
    ("bearing_rail_L", "bearing_rail_L"),
    ("bearing_rail_R", "bearing_rail_R"),
    ("shaft_5mm", "shaft_5mm"),
] + [(f"spacer_{i}", f"spacer_{i}") for i in range(1, 7)]

SHELL_KEYS = [
    ("inlet_spike", "inlet_spike"),
    ("combustor_shell", "combustor_liner"),
    ("afterburner_shell", "afterburner_case"),
    ("nozzle_cone", "nozzle_cone"),
    ("aft_cap", "aft_cap"),
    ("casing_front", "outer_casing"),
    ("casing_mid", "outer_casing"),
    ("casing_aft", "outer_casing"),
    ("splice_front_mid", "splice_front_mid"),
    ("splice_mid_aft", "splice_mid_aft"),
    ("pylon_mount_front", "pylon_mount_front"),
    ("pylon_mount_aft", "pylon_mount_aft"),
]

def _pick_paths(meta: dict, tag: str, kind: str) -> list[str]:
    names = [p["name"] for p in meta["parts"]]

    def choose(keys: list[tuple[str, str]]) -> list[str]:
        outs: list[str] = []
        for k_new, k_old in keys:
            # 우선순위: 새이름+태그 -> 새이름 -> 구이름+태그 -> 구이름
            cands = [k_new + tag, k_new, k_old + tag, k_old]
            hit = None
            for c in cands:
                hit = next((p for p in meta["parts"] if p["name"].startswith(c)), None)
                if hit: break
            if hit: outs.append(hit["path"])
        return outs

    if kind == "core":   return choose(CORE_KEYS)
    if kind == "shells": return choose(SHELL_KEYS)
    # all
    return [p["path"] for p in meta["parts"]
            if (tag in p["name"]) or ("_R" not in p["name"] and "_L" not in p["name"])]

# ---------- 스프루(러너) 생성 ----------
def frame_grid(plate_w: float, plate_d: float, bar_w: float, margin: float,
               cols: int, rows: int, z: float) -> tm.Trimesh:
    """바깥 테두리 + 내부 격자 바"""
    beams: List[tm.Trimesh] = []
    t = bar_w  # 높이 = bar_w (세로로 3mm 같은 값)
    # 외곽
    # 위/아래
    for y in [margin, plate_d - margin - bar_w]:
        b = tm.creation.box(extents=[plate_w - 2 * margin, bar_w, t])
        b.apply_translation([plate_w * 0.5, y + bar_w * 0.5, z + t * 0.5])
        beams.append(b)
    # 좌/우
    for x in [margin, plate_w - margin - bar_w]:
        b = tm.creation.box(extents=[bar_w, plate_d - 2 * margin, t])
        b.apply_translation([x + bar_w * 0.5, plate_d * 0.5, z + t * 0.5])
        beams.append(b)
    # 내부 세로 격자
    cell_w = (plate_w - 2 * margin - (cols - 1) * bar_w) / cols
    x = margin
    for c in range(cols - 1):
        x += cell_w + bar_w
        b = tm.creation.box(extents=[bar_w, plate_d - 2 * margin, t])
        b.apply_translation([x + bar_w * 0.5, plate_d * 0.5, z + t * 0.5])
        beams.append(b)
    # 내부 가로 격자
    cell_d = (plate_d - 2 * margin - (rows - 1) * bar_w) / rows
    y = margin
    for r in range(rows - 1):
        y += cell_d + bar_w
        b = tm.creation.box(extents=[plate_w - 2 * margin, bar_w, t])
        b.apply_translation([plate_w * 0.5, y + bar_w * 0.5, z + t * 0.5])
        beams.append(b)
    return tm.util.concatenate(beams)

def place_to_cells(meshes: List[tm.Trimesh], plate_w: float, plate_d: float,
                   margin: float, bar_w: float, cols: int, rows: int,
                   z0: float, pad: float = 1.5) -> list[list[tuple[tm.Trimesh, Tuple[int,int,Tuple[float,float,float,float]]]]]:
    """
    return: pages -> [(mesh, (col,row,(cell_x0,cell_y0,cell_w,cell_d)))]
    """
    pages: list[list[tuple[tm.Trimesh, Tuple[int,int,Tuple[float,float,float,float]]]]] = []
    capacity = cols * rows
    # 셀 크기
    cell_w = (plate_w - 2 * margin - (cols - 1) * bar_w) / cols
    cell_d = (plate_d - 2 * margin - (rows - 1) * bar_w) / rows

    def fit_one(m: tm.Trimesh) -> tm.Trimesh:
        # 바닥을 0으로 정렬
        m2 = m.copy()
        minx, miny, minz = m2.bounds[0]
        m2.apply_translation([-minx, -miny, -minz])
        # 셀에 맞추어 90도 회전 검사
        sx, sy, _ = m2.extents
        ok = (sx + 2 * pad <= cell_w) and (sy + 2 * pad <= cell_d)
        if not ok:
            # 90도 회전
            m3 = m2.copy()
            Rz = tm.transformations.rotation_matrix(np.deg2rad(90), [0, 0, 1])
            m3.apply_transform(Rz)
            sx2, sy2, _ = m3.extents
            if (sx2 + 2 * pad <= cell_w) and (sy2 + 2 * pad <= cell_d):
                m2 = m3
                sx, sy = sx2, sy2
            else:
                raise RuntimeError(f"part too large for cell ({sx:.1f}×{sy:.1f} > {cell_w:.1f}×{cell_d:.1f})")
        # 셀 중앙 배치
        dx = (cell_w - sx) * 0.5
        dy = (cell_d - sy) * 0.5
        m2.apply_translation([dx, dy, z0])
        return m2

    # 페이지 분할
    for i in range(0, len(meshes), capacity):
        chunk = meshes[i:i + capacity]
        page: list[tuple[tm.Trimesh, Tuple[int,int,Tuple[float,float,float,float]]]] = []
        for k, m in enumerate(chunk):
            col = k % cols
            row = k // cols
            # 셀 원점
            x0 = margin + col * (cell_w + bar_w)
            y0 = margin + row * (cell_d + bar_w)
            m2 = fit_one(m)
            m2.apply_translation([x0, y0, 0])
            page.append((m2, (col, row, (x0, y0, cell_w, cell_d))))
        pages.append(page)
    return pages

def make_gate_to_wall(mesh: tm.Trimesh, cell_info: Tuple[float,float,float,float],
                      bar_w: float, gate_w: float, gate_h: float, z0: float) -> tm.Trimesh:
    """가장 가까운 셀 벽에 짧은 게이트 생성(직사각형 바)"""
    x0, y0, cw, cd = cell_info
    minx, miny, minz = mesh.bounds[0]
    maxx, maxy, maxz = mesh.bounds[1]
    # 벽까지 거리
    dL = (minx - x0)                # 왼쪽
    dR = (x0 + cw - maxx)           # 오른쪽
    dB = (miny - y0)                # 아래
    dT = (y0 + cd - maxy)           # 위
    dists = [("L", dL), ("R", dR), ("B", dB), ("T", dT)]
    side, dist = min(dists, key=lambda t: t[1])
    dist = max(1.0, float(dist))    # 안전 여유
    zc = z0 + gate_h * 0.5          # 게이트 높이 중앙

    if side in ("L", "R"):
        # x방향으로 벽에 닿게
        glen = dist + bar_w * 0.5
        if side == "L":
            cx = minx - glen * 0.5
        else:
            cx = maxx + glen * 0.5
        cy = (miny + maxy) * 0.5
        gate = tm.creation.box(extents=[glen, gate_w, gate_h])
        gate.apply_translation([cx, cy, zc])
    else:
        glen = dist + bar_w * 0.5
        if side == "B":
            cy = miny - glen * 0.5
        else:
            cy = maxy + glen * 0.5
        cx = (minx + maxx) * 0.5
        gate = tm.creation.box(extents=[gate_w, glen, gate_h])
        gate.apply_translation([cx, cy, zc])
    return gate

# ---------- 파라미터 & 빌더 ----------
class SprueParam(BaseModel):
    # 어떤 런에서 가져올지(생략 시 최신 자동)
    out_dir: str | None = None
    # R / L / (빈문자면 공통)
    engine_tag: str = "R"
    # "core" / "shells" / "all"
    set: str = "core"

    # 판 크기 & 프레임/격자
    plate_w: float = 220.0
    plate_d: float = 220.0
    margin: float = 8.0
    bar_w: float = 3.0    # 격자/프레임 바의 두께(폭/높이)

    # 셀 구성
    cols: int = 3
    rows: int = 3
    z0: float = 2.0       # 판(0~z0는 평판), 그 위로 부품/게이트

    # 게이트 규격
    gate_w: float = 1.6
    gate_h: float = 1.6

def build_sprue(p: SprueParam) -> dict:
    meta, run_dir, flavor = _load_meta(p.out_dir)
    if not meta:
        return {"ok": False, "reason": "no_run_found"}

    tag = "_" + p.engine_tag if p.engine_tag else ""
    paths = _pick_paths(meta, tag, p.set)
    if not paths:
        return {"ok": False, "reason": "no_parts_for_set", "set": p.set}

    meshes = [load_mesh(x) for x in paths]
    pages = place_to_cells(meshes, p.plate_w, p.plate_d,
                           p.margin, p.bar_w, p.cols, p.rows, p.z0)

    out_root = os.path.join(
        run_dir,
        f"sprue_{p.set}_{p.engine_tag or 'X'}_{int(p.plate_w)}x{int(p.plate_d)}_{p.cols}x{p.rows}"
    )
    os.makedirs(out_root, exist_ok=True)

    out_items = []
    for i, page in enumerate(pages, start=1):
        # 프레임/격자
        grid = frame_grid(p.plate_w, p.plate_d, p.bar_w, p.margin, p.cols, p.rows, p.z0)

        # 파트 + 게이트
        geoms: List[tm.Trimesh] = [grid]
        for m, (_c, _r, cell_rect) in page:
            geoms.append(m)
            geoms.append(make_gate_to_wall(m, cell_rect, p.bar_w, p.gate_w, p.gate_h, p.z0))

        # 베이스 플레이트
        plate = rect_plate(p.plate_w, p.plate_d, p.z0)

        sc = tm.Scene()
        sc.add_geometry(plate)
        for g in geoms: sc.add_geometry(g)

        sub = os.path.join(out_root, f"page_{i:02d}")
        os.makedirs(sub, exist_ok=True)
        glb = os.path.join(sub, "sprue.glb")
        stl = os.path.join(sub, "sprue_merged.stl")
        sc.export(glb)
        tm.util.concatenate([plate] + geoms).export(stl)

        out_items.append({"page": i, "glb": glb, "stl": stl, "dir": sub})

    info = {
        "ok": True,
        "pages": out_items,
        "count": len(out_items),
        "out_root": out_root,
        "source_run": run_dir,
        "flavor": flavor,
        "hint": "게이트는 얇게 설계됨(니퍼로 절단). 필요 시 gate_w/h 조정."
    }
    with open(os.path.join(out_root, "sprue_index.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return info

# ---------- FastAPI 라우터 ----------
api = APIRouter(prefix="/wb")

@api.post("/cad/j58_v23_sprue")
def j58_v23_sprue(p: SprueParam = Body(SprueParam())):
    return build_sprue(p)

@api.get("/files/{rel_path:path}")
def send_file(rel_path: str):
    full = _safe(rel_path)
    if not full or not os.path.exists(full):
        return JSONResponse({"ok": False, "reason": "not_found", "rel": rel_path}, status_code=404)
    return FileResponse(full)
