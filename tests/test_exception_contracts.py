from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.main import create_app
from app.security import rate_limiter


class _AuthServiceStub:
    def __init__(self, vendor_id: int) -> None:
        self.vendor_id = vendor_id

    def decode_token(self, token: str) -> int:
        return self.vendor_id


def _assert_error_shape(payload: dict) -> None:
    assert "error" in payload
    error = payload["error"]
    assert isinstance(error.get("code"), str)
    assert isinstance(error.get("message"), str)
    assert isinstance(error.get("details"), dict)


def test_exception_response_shape_validation_error() -> None:
    rate_limiter.reset()
    client = TestClient(create_app())
    response = client.get("/auth/google/callback")

    assert response.status_code == 400
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["error"]["code"] == "validation_error"


def test_exception_response_shape_authorization_error() -> None:
    rate_limiter.reset()
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: _AuthServiceStub(vendor_id=1)
    client = TestClient(app)

    response = client.get("/vendors/2/products", headers={"Authorization": "Bearer token"})

    assert response.status_code == 403
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["error"]["code"] == "authorization_error"


def test_exception_response_shape_not_found_error() -> None:
    rate_limiter.reset()
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: _AuthServiceStub(vendor_id=999)
    client = TestClient(app)

    response = client.get("/vendors/999/products", headers={"Authorization": "Bearer token"})

    assert response.status_code == 404
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["error"]["code"] == "resource_not_found"
