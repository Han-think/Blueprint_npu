# Example assemblies for quick demo
PRESETS = {
  "rocket_3stage_demo": {
    "rocket": {
      "payload_mass": 2000.0,
      "stages": [
        {"name": "S1", "samples": 256, "topk": 8, "prop_mass": 120000.0, "dry_mass": 10000.0},
        {"name": "S2", "samples": 256, "topk": 8, "prop_mass": 30000.0, "dry_mass": 3000.0},
        {"name": "S3", "samples": 256, "topk": 8, "prop_mass": 6000.0, "dry_mass": 800.0}
      ]
    }
  },
  "pencil_fighter_demo": {
    "pencil": {
      "samples": 256,
      "topk": 8,
      "M0": 0.9,
      "alt_m": 2000.0,
      "airframe": {"mass_kg": 11000.0, "fuel_kg": 3200.0},
      "ramjet_boost": {"enable": True, "M_on": 1.8, "gain_pct": 18.0}
    }
  },
  "hybrid_full_demo": {
    "rocket": {
      "payload_mass": 1500.0,
      "stages": [
        {"name": "S1", "samples": 128, "topk": 4, "prop_mass": 90000.0, "dry_mass": 8000.0},
        {"name": "S2", "samples": 128, "topk": 4, "prop_mass": 25000.0, "dry_mass": 2500.0},
        {"name": "S3", "samples": 128, "topk": 4, "prop_mass": 5000.0, "dry_mass": 700.0}
      ]
    },
    "pencil": {
      "samples": 128,
      "topk": 4,
      "M0": 0.85,
      "alt_m": 1500.0,
      "airframe": {"mass_kg": 10000.0, "fuel_kg": 2800.0},
      "ramjet_boost": {"enable": True, "M_on": 1.6, "gain_pct": 12.0}
    }
  }
}
