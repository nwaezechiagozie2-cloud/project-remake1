from functools import lru_cache

from app.config import get_settings
from app.repositories.sql import (
    SQLCustomerRepository,
    SQLGoogleTokenRepository,
    SQLKnowledgeRepository,
    SQLProductRepository,
    SQLVendorRepository,
    SQLVendorSettingsRepository,
)
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService
from app.services.google_contacts_service import GoogleContactsService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.webhook_service import WebhookService
from app.services.whatsapp_service import WhatsAppService


@lru_cache(maxsize=1)
def get_vendor_repo() -> SQLVendorRepository:
    return SQLVendorRepository()


@lru_cache(maxsize=1)
def get_product_repo() -> SQLProductRepository:
    return SQLProductRepository()


@lru_cache(maxsize=1)
def get_customer_repo() -> SQLCustomerRepository:
    return SQLCustomerRepository()


@lru_cache(maxsize=1)
def get_settings_repo() -> SQLVendorSettingsRepository:
    return SQLVendorSettingsRepository()


@lru_cache(maxsize=1)
def get_knowledge_repo() -> SQLKnowledgeRepository:
    return SQLKnowledgeRepository()


@lru_cache(maxsize=1)
def get_google_token_repo() -> SQLGoogleTokenRepository:
    return SQLGoogleTokenRepository()


def get_auth_service() -> AuthService:
    return AuthService(settings=get_settings(), vendors=get_vendor_repo())


def get_agent_service() -> AgentService:
    return AgentService(
        settings=get_settings(),
        products=get_product_repo(),
        knowledge=get_knowledge_repo(),
        customers=get_customer_repo(),
        vendor_settings=get_settings_repo(),
    )


def get_google_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService(settings=get_settings(), vendors=get_vendor_repo(), tokens=get_google_token_repo())


def get_webhook_service() -> WebhookService:
    return WebhookService(
        vendors=get_vendor_repo(),
        customers=get_customer_repo(),
        contacts=GoogleContactsService(get_settings(), get_google_token_repo()),
        agent=get_agent_service(),
        whatsapp=WhatsAppService(get_settings()),
    )
