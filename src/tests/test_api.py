from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health_check():
    """Verifica que el endpoint de salud responda correctamente."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_calendar_ics_structure():
    """Verifica que se genere un archivo ICS válido."""
    response = client.get("/calendar.ics")
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    assert "BEGIN:VCALENDAR" in response.text
    assert "END:VCALENDAR" in response.text

def test_get_calendar_filtering():
    """Verifica que los filtros de categoría funcionen (sin romper la app)."""
    response = client.get("/calendar.ics?cats=f1")
    assert response.status_code == 200
    # Debería contener eventos si hay datos de F1, o al menos el header del calendario
    assert "BEGIN:VCALENDAR" in response.text

def test_static_files_serve():
    """Verifica que el frontend se sirva en la raíz."""
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text