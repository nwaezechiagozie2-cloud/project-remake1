import re
from io import BytesIO
from decimal import Decimal, InvalidOperation

from app.domain.interfaces import CatalogueRepository
from app.exceptions import ValidationError


SUPPORTED_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class CatalogueIngestionService:
    def __init__(self, catalogue: CatalogueRepository) -> None:
        self._catalogue = catalogue

    async def ingest_file(self, vendor_id: int, file_name: str, mime_type: str | None, content: bytes) -> dict:
        if not content:
            raise ValidationError("Catalogue file is empty")
        if mime_type and mime_type not in SUPPORTED_MIME_TYPES:
            raise ValidationError("Unsupported catalogue file type", details={"mime_type": mime_type})

        upload = await self._catalogue.create_upload(
            vendor_id,
            {
                "file_name": file_name,
                "mime_type": mime_type,
                "status": "PROCESSING",
            },
        )

        try:
            extracted_text = self._extract_text(file_name, mime_type, content)
            candidates = self._parse_product_candidates(extracted_text)
            updated = await self._catalogue.mark_upload_processed(
                vendor_id,
                upload["id"],
                extracted_text,
                candidates,
            )
            return updated or upload
        except Exception as exc:
            await self._catalogue.mark_upload_failed(vendor_id, upload["id"], str(exc))
            raise

    def _extract_text(self, file_name: str, mime_type: str | None, content: bytes) -> str:
        normalized_name = file_name.lower()
        if (mime_type or "").startswith("text/") or normalized_name.endswith((".txt", ".csv")):
            return content.decode("utf-8", errors="replace").strip()

        if mime_type == "application/pdf" or normalized_name.endswith(".pdf"):
            return self._extract_pdf_text(content)

        if mime_type in {
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        } or normalized_name.endswith((".doc", ".docx")):
            if normalized_name.endswith(".doc") and not normalized_name.endswith(".docx"):
                raise ValidationError("Old .doc files are not supported yet. Upload PDF, TXT, CSV, or DOCX.")
            return self._extract_docx_text(content)

        raise ValidationError("Unsupported catalogue file type", details={"mime_type": mime_type})

    def _parse_product_candidates(self, extracted_text: str) -> list[dict]:
        candidates: list[dict] = []
        seen_names: set[str] = set()

        for raw_line in extracted_text.splitlines():
            line = " ".join(raw_line.strip().split())
            if len(line) < 3:
                continue

            price = self._extract_price(line)
            if price is None:
                continue

            name = self._clean_product_name(line)
            if len(name) < 2:
                continue

            name_key = name.lower()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            candidates.append(
                {
                    "name": name[:255],
                    "description": None,
                    "price": price,
                    "currency": "NGN",
                    "in_stock": not self._looks_unavailable(line),
                    "raw_text": line,
                    "status": "DRAFT",
                }
            )

        return candidates[:200]

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValidationError("PDF support requires pypdf. Run: pip install pypdf") from exc

        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text = "\n".join(page for page in pages if page)
        if not text:
            raise ValidationError("No selectable text found in this PDF")
        return text

    def _extract_docx_text(self, content: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise ValidationError("DOCX support requires python-docx. Run: pip install python-docx") from exc

        document = Document(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        text = "\n".join(paragraphs)
        if not text:
            raise ValidationError("No text found in this DOCX")
        return text

    def _extract_price(self, line: str) -> Decimal | None:
        match = re.search(r"(?:NGN|N|₦)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", line, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return Decimal(match.group(1).replace(",", ""))
        except InvalidOperation:
            return None

    def _clean_product_name(self, line: str) -> str:
        cleaned = re.sub(r"(?:NGN|N|₦)?\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?", "", line, count=1, flags=re.IGNORECASE)
        cleaned = re.sub(r"^[\-*•\d\.\)\s]+", "", cleaned)
        cleaned = re.sub(r"\b(in stock|available|out of stock|sold out|unavailable)\b", "", cleaned, flags=re.IGNORECASE)
        return " ".join(cleaned.replace(" - ", " ").replace(":", " ").split())

    def _looks_unavailable(self, line: str) -> bool:
        return bool(re.search(r"\b(out of stock|sold out|unavailable)\b", line, flags=re.IGNORECASE))
