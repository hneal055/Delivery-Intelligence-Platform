from fastapi.testclient import TestClient

def test_predict_eta(client: TestClient, normal_user_token_headers):
    payload = {
        "distance_km": 5.0,
        "traffic_load": 0.5,
        "num_packages": 2
    }
    response = client.post(
        "/analytics/predict-eta", 
        json=payload, 
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "estimated_minutes" in data
    assert "confidence_score" in data
    assert data["estimated_minutes"] > 0

def test_predict_eta_invalid_input(client: TestClient, normal_user_token_headers):
    payload = {
        "distance_km": -10.0, # Invalid
        "traffic_load": 0.5,
        "num_packages": 2
    }
    response = client.post(
        "/analytics/predict-eta", 
        json=payload, 
        headers=normal_user_token_headers
    )
    assert response.status_code == 400

