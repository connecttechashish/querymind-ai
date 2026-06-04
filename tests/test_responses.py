from querymindai_backend.models import RootResponse, HealthResponse

def test_root_response():
    resp = RootResponse(message="Hello", app_name="QueryMind AI", version="0.1.0")
    assert resp.message == "Hello"
    assert resp.app_name == "QueryMind AI"
    assert resp.version == "0.1.0"

def test_health_response():
    resp = HealthResponse(
        status="healthy",
        app_name="QueryMind AI",
        version="0.1.0",
        environment="development",
    )
    assert resp.status == "healthy"
    assert resp.app_name == "QueryMind AI"
    assert resp.version == "0.1.0"
    assert resp.environment == "development"
