import os
import logging
import requests

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_API_URL")

if not API_TOKEN or not BACKEND_URL:
    logger.error("Необходимо задать TELEGRAM_BOT_TOKEN и BACKEND_API_URL в .env файле")
    exit()

# --- Хендлеры (обработчики команд и сообщений) ---


async def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение при команде /start или /help."""
    welcome_text = (
        "Здравствуйте! 👋\n\n"
        "Я ваш персональный ассистент по магистерским программам ИТМО "
        "в области искусственного интеллекта.\n\n"
        "Я могу:\n"
        "✅ Рассказать об отличиях программ 'Искусственный интеллект' и 'AI Product Management'.\n"
        "✅ Показать учебные планы и описать дисциплины.\n"
        "✅ Помочь с выбором курсов на основе вашего бэкграунда.\n\n"
        "Просто задайте мне свой вопрос!"
    )
    await update.message.reply_text(welcome_text)


async def handle_text_message(update: Update, context: CallbackContext) -> None:
    """Пересылает текстовое сообщение пользователя на бэкенд и возвращает ответ."""
    chat_id = str(update.effective_chat.id)
    query_text = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    payload = {"chat_id": chat_id, "query_text": query_text}

    try:
        response = requests.post(BACKEND_URL, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        answer = data.get("answer", "Не удалось получить ответ от сервера.")

        await update.message.reply_text(answer, parse_mode="MARKDOWN")

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Ошибка статуса от API: {e.response.status_code} - {e.response.text}"
        )
        await update.message.reply_text(
            "Прошу прощения, на сервере произошла ошибка. Попробуйте повторить запрос позже."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка подключения к API: {e}")
        await update.message.reply_text(
            "Не могу связаться с сервером. Пожалуйста, проверьте, что сервис запущен и доступен."
        )
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}")
        await update.message.reply_text(
            "Что-то пошло не так. Мы уже разбираемся в проблеме."
        )


def main() -> None:
    """Основная функция для запуска бота."""
    application = Application.builder().token(API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    logger.info("Запуск Telegram-бота...")
    application.run_polling()


if __name__ == "__main__":
    main()
