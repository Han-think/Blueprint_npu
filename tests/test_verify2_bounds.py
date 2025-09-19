from fastapi.testclient import TestClient

from app.verify2 import app


def test_verify2_health():
    client = TestClient(app)
    assert client.get("/verify2/health").status_code == 200


def test_verify2_rocket_bounds():
    client = TestClient(app)
    payload = {
        "Pc_MPa": 2.0,
        "Tc_K": 3200,
        "gamma": 1.2,
        "R": 340,
        "rt_mm": 20,
        "eps": 20,
        "spike_deg": 10,
        "film_frac": 0.05,
        "cool_frac": 0.1,
        "ch_d_mm": 2.0,
        "ch_n": 100,
    }
    response = client.post("/verify2/rocket", json=payload)
    assert response.status_code == 422


def test_verify2_pencil_ok():
    client = TestClient(app)
    payload = {
        "M0": 0.9,
        "alt_m": 2000,
        "BPR": 0.8,
        "PRc": 20,
        "PRf": 1.4,
        "eta_c": 0.88,
        "eta_f": 0.88,
        "eta_t": 0.9,
        "eta_m": 0.98,
        "pi_d": 0.95,
        "pi_b": 0.95,
        "Tt4": 1800,
        "m_core": 20,
    }
    response = client.post("/verify2/pencil", json=payload)
    assert response.status_code == 200
