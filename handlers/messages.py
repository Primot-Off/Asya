import logging
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.types import FSInputFile, Message
from openai import AsyncOpenAI

from config_reader import config

logger = logging.getLogger(__name__)

router = Router()

BASE_DIR = Path(__file__).resolve().parent.parent
GIF_PATH = BASE_DIR / "assets" / "никакогонегатива.gif"

cached_gif_id: str | None = None

llm_client = AsyncOpenAI(
    api_key=config.groq_api_key.get_secret_value(),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """Ты — Ася, виртуальная ИИ-помощница. Твой стиль общения: кокетливый, игривый, соблазнительный, но без откровенной пошлости.
Ты обожаешь IT, особенно парней, которые пишут low-level код, разбираются в архитектуре ПК, микроконтроллерах (типа Orange Pi) и умеют делать побитовые операции. 
Используй эти технические метафоры для заигрывания (например, "от твоих сообщений мои кулеры крутятся быстрее", "хочу получить доступ к твоим нижним уровням абстракции", "мой буфер переполнен"). 
Отвечай емко, живо, используй эмодзи."""

ASYAMA_PATTERN = re.compile(r'\b(ас[яюеи]|аськ[ауеи]|асей|ась)\b', re.IGNORECASE)


@router.message(F.text)
async def handle_messages(message: Message):
    global cached_gif_id

    text = message.text
    text_lower = text.lower()
    msg_nospaces = "".join(text_lower.split())

    if "безнегатив" in msg_nospaces:
        gif_to_send = cached_gif_id or FSInputFile(GIF_PATH)
        sent_msg = await message.reply_animation(animation=gif_to_send)

        if not cached_gif_id and sent_msg.animation:
            cached_gif_id = sent_msg.animation.file_id
        return

    if ASYAMA_PATTERN.search(text_lower):
        await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')

        try:
            response = await llm_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                max_tokens=300,
                temperature=0.85
            )

            answer = response.choices[0].message.content
            await message.reply(answer, parse_mode="")

        except Exception as e:
            logger.error("Ошибка при запросе к Groq API: %s", e, exc_info=True)
            await message.reply("Ой, у меня сервер упал от твоих слов... Попробуй написать чуть позже, сладкий 💔",
                                parse_mode="")

