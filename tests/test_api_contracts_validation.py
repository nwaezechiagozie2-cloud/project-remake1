import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.schemas.api import ProductCreateRequest, ProductUpdateRequest


def test_product_create_validation_rejects_invalid_currency() -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Desk Lamp",
            price=10000,
            currency="ngn",
        )


def test_product_create_validation_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Desk Lamp",
            price=10000,
            currency="NGN",
            image_url="not-a-url",
        )


def test_product_update_validation_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        ProductUpdateRequest(price=-2)


def test_openapi_includes_error_code_docs_for_auth_and_vendor_admin() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    payload = openapi.json()

    auth_400 = payload["paths"]["/auth/register"]["post"]["responses"]["400"]
    vendor_401 = payload["paths"]["/vendors/{vendor_id}/products"]["get"]["responses"]["401"]

    assert "validation_error" in str(auth_400)
    assert "authentication_error" in str(vendor_401)


def test_openapi_includes_webhook_request_example() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    payload = openapi.json()

    request_example = payload["paths"]["/webhook"]["post"]["requestBody"]["content"]["application/json"]["example"]
    assert request_example["object"] == "whatsapp_business_account"
    assert request_example["entry"][0]["changes"][0]["value"]["messages"][0]["type"] == "text"
