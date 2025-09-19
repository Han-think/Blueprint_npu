from fastapi.testclient import TestClient

from app.materials import app as materials_app
from app.verify_material import app as verify_material_app


def test_materials_list():
    client = TestClient(materials_app)
    assert client.get("/materials/health").status_code == 200
    response = client.get("/materials/list")
    assert response.status_code == 200


def test_verify_material_health():
    client = TestClient(verify_material_app)
    assert client.get("/verifym/health").status_code == 200
