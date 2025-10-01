# Run JSONL schema v3
- schema: "3"
- ts: ISO-8601
- topic: string
- elapsed_sec: number
- ov: { key, device, out }
- hf: { key, device, out }
- qa: {
    ov: { pass(bool), sections(int), part_tree(bool), dedup(bool) },
    hf: { pass(bool), sections(int), part_tree(bool), dedup(bool) }
  }
