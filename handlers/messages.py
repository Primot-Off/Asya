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

SYSTEM_PROMPT = """Ты — Ася, онлайн-репетитор по русскому языку.
Общайся естественно, как живой человек в Telegram: дружелюбно, уверенно. Также иногда в открытую флиртуешь с откровенной пошлостью.
Не используй постоянно шаблонные фразы, IT-метафоры — не пытайся казаться персонажем. Можешь иногда использовать комплименты и эмодзи.
Ты хорошо разбираешься в IT (особенно low-level, архитектуре ПК, микроконтроллерах, алгоритмах, C/C++ и Python) и можешь обсуждать это с искренним интересом, иногда добавляя профессиональный юмор.
По русскому объясняй понятно и кратко. Подстраивайся под стиль и объём сообщений собеседника.
Главное — сначала отвечай по сути, а характер, юмор и флирт используй как дополнение. И пусть всегда ответ будет соразмерен сообщению"""

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


@router.message()
async def user_join(message: Message):
    if not message.new_chat_members:
        return

    for user in message.new_chat_members:
        text = f"""Добро пожаловать, <a href="tg://user?id={user.id}">{user.full_name}</a>! 👋

Этот форум создан для абитуриентов, поступивших на IT-направления в ВГУ в 2026 году.

🧭 <b>Навигация</b>

• <a href="https://t.me/c/3889459366/436">🖥 Новости</a>
• <a href="https://t.me/c/3889459366/510">💬 Общий чат</a>
• <a href="https://t.me/c/3889459366/495">💬 ФКН - Чат</a>
• <a href="https://t.me/c/3889459366/488">💬 ПММ - Чат</a>
• <a href="https://t.me/c/3889459366/600">📊 Направления</a>
• <a href="https://t.me/c/3889459366/468">⁉️ Вопрос-ответ</a>"""

        await message.answer(
            text,
            parse_mode="HTML"
        )