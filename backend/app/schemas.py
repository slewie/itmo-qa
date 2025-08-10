from pydantic import BaseModel
from typing import Optional, List


class QueryRequest(BaseModel):
    """Модель запроса к чат-боту."""

    chat_id: (
        str  # Используем str для универсальности (TG ID - int, но может быть и UUID)
    )
    query_text: str


class SourceDocument(BaseModel):
    """Модель для исходного документа, на основе которого дан ответ."""

    page_content: str
    metadata: dict


class QueryResponse(BaseModel):
    """Модель ответа от чат-бота."""

    answer: str
    source_documents: Optional[List[SourceDocument]] = None
