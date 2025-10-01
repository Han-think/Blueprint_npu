## BLUEPRINT package
- Design Brief
- Interfaces & tolerances (mates/seals/fits)
- Geometry notes (key Ø/angles; walls 0.6–1.2 mm; channels ≥1.2 mm radius; overhang ≤45°)
- Manufacturing notes (AM orientation, supports, HIP/HT, machining datums)
- Test Plan (sequence, sensors PT/TC/LL/ACC, acceptance criteria)
- Top-5 risks & probes
`part_tree
{"id":"ASM-001","name":"Assembly","qty":1,"material":"Inconel 718","process":"L-PBF",
 "children":[
   {"id":"C-001","name":"Cowl","qty":1,"material":"Inconel 718","process":"L-PBF","children":[]},
   {"id":"HX-001","name":"Heat-Exchanger","qty":1,"material":"CuCrZr","process":"L-PBF","children":[]}
 ]}
