import struct, os
from pathlib import Path
import argparse

def write_cube_stl(path, size=10.0):
    # 단순 큐브(12삼각형) 바이너리 STL
    s = size/2.0
    verts = [
        (-s,-s,-s),( s,-s,-s),( s, s,-s),(-s, s,-s),  # 바닥 z-
        (-s,-s, s),( s,-s, s),( s, s, s),(-s, s, s)   # 천장 z+
    ]
    faces = [
        (0,1,2),(0,2,3),   # z-
        (4,6,5),(4,7,6),   # z+
        (0,4,5),(0,5,1),   # y-
        (2,6,7),(2,7,3),   # y+
        (1,5,6),(1,6,2),   # x+
        (0,3,7),(0,7,4)    # x-
    ]
    with open(path, "wb") as f:
        f.write(b'cube_stl'+b'\0'*(80-8))
        f.write(struct.pack("<I", len(faces)))
        for a,b,c in faces:
            nx,ny,nz = 0.0,0.0,0.0
            f.write(struct.pack("<3f", nx,ny,nz))
            for i in (a,b,c):
                f.write(struct.pack("<3f", *verts[i]))
            f.write(struct.pack("<H", 0))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_stl", required=True)
    ap.add_argument("--size", type=float, default=10.0)
    args = ap.parse_args()
    Path(os.path.dirname(args.out_stl)).mkdir(parents=True, exist_ok=True)
    write_cube_stl(args.out_stl, args.size)