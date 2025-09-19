from fastapi.testclient import TestClient

from app.verify import app


def test_verify_health_and_dummy() -> None:
    client = TestClient(app)
    assert client.get("/verify/health").status_code == 200

    payload = {
        "Pc_MPa": 10.0,
        "Tc_K": 3200.0,
        "gamma": 1.2,
        "R": 340.0,
        "rt_mm": 20.0,
        "eps": 20.0,
        "spike_deg": 10.0,
        "film_frac": 0.05,
        "cool_frac": 0.1,
        "ch_d_mm": 2.0,
        "ch_n": 100,
    }
    response = client.post("/verify/rocket", json=payload)
    assert response.status_code == 200
