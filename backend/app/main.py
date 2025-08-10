from fastapi import FastAPI, HTTPException
from typing import Dict

from .schemas import QueryRequest, QueryResponse
from .rag_core import rag_core_instance

app = FastAPI(
    title="ITMO Magistracy QA Bot API",
    description="API для чат-бота, помогающего абитуриентам ИТМО.",
    version="1.0.0",
)

CONVERSATION_STATE: Dict[str, Dict] = {}


@app.get("/", tags=["Health Check"])
def health_check():
    """Проверка доступности сервиса."""
    return {"status": "ok"}


@app.post("/v1/chat", response_model=QueryResponse, tags=["Chat"])
async def process_chat_query(request: QueryRequest):
    """
    Основной эндпоинт для обработки запросов от чат-бота.
    Реализует простую логику управления состоянием для получения рекомендаций.
    """
    chat_id = request.chat_id
    query = request.query_text.lower()

    if (
        "посоветуй" in query
        or "порекомендуй" in query
        or "какие курсы выбрать" in query
    ):
        if (
            chat_id in CONVERSATION_STATE
            and "background" in CONVERSATION_STATE[chat_id]
        ):
            user_background = CONVERSATION_STATE[chat_id]["background"]
            result = rag_core_instance.get_recommendations(user_background)
            return QueryResponse(**result)
        else:
            CONVERSATION_STATE[chat_id] = {"state": "awaiting_background"}
            answer = "Конечно, я могу помочь с выбором курсов! Расскажите, пожалуйста, о своем опыте и знаниях. Например: 'Я python-разработчик с 2-летним опытом, хорошо знаю ML-фреймворки' или 'Я менеджер проектов без технического бэкграунда'."
            return QueryResponse(answer=answer)

    if (
        chat_id in CONVERSATION_STATE
        and CONVERSATION_STATE[chat_id].get("state") == "awaiting_background"
    ):
        CONVERSATION_STATE[chat_id] = {"background": request.query_text}
        answer = "Спасибо! Я сохранил информацию о вашем бэкграунде. Теперь можете снова попросить меня порекомендовать курсы."
        return QueryResponse(answer=answer)

    try:
        result = rag_core_instance.answer_query(request.query_text)
        return QueryResponse(**result)
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при обработке вашего запроса.",
        )
