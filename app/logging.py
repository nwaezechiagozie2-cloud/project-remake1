import logging
import re

from app.observability import get_correlation_id


class RedactingFilter(logging.Filter):
    PHONE_PATTERN = re.compile(r"\+?\d{10,15}")
    SENSITIVE_KV_PATTERN = re.compile(
        r"(?i)\b(authorization|token|access_token|refresh_token|secret|password|api_key)\b\s*[:=]\s*([^\s,;]+)"
    )
    BEARER_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")

    @classmethod
    def _redact(cls, value: str) -> str:
        redacted = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", value)
        redacted = cls.SENSITIVE_KV_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
        redacted = cls.BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
        return redacted

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        message = record.getMessage()
        sanitized = self._redact(message)
        record.msg = sanitized
        record.args = ()
        return True


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | corr=%(correlation_id)s | %(name)s | %(message)s",
    )

    redacting_filter = RedactingFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(redacting_filter)
