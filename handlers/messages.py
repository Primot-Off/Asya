import logging
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import mistune
from collections import deque, defaultdict

from aiogram import F, Router
from aiogram.types import FSInputFile, Message
from openai import AsyncOpenAI
from aiogram.enums import ParseMode

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
В групповом чате сообщения пользователей будут начинаться с их имени (Например, Иван: привет). Обращайся к ним по именам, если это уместно.
Главное — сначала отвечай по сути, а характер, юмор и флирт используй как дополнение. И пусть всегда ответ будет соразмерен сообщению"""

ASYAMA_PATTERN = re.compile(r'\b(ас[яюеи]|аськ[ауеи]|асей|ась)\b', re.IGNORECASE)

user_memory = defaultdict(lambda: deque(maxlen=10)) # Больше maxlen - больше память. попробуй 20-30.

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

    if "врем" in msg_nospaces:
        return await message.reply(f"Сейчас {datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M")} по Московскому времени")

    if "насрал" in msg_nospaces:
            return await message.reply("Убери")

    if ASYAMA_PATTERN.search(text_lower):
        await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')

        history = user_memory[message.chat.id]
        formatted_user_text = f"{message.from_user.first_name}: {text}"
        history.append({"role": "user", "content" : formatted_user_text})
        messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)
        
        try:
            response = await llm_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages_to_send,
                max_tokens=300,
                temperature=0.85
            )

            answer = response.choices[0].message.content

            history.append({"role": "assistant", "content": answer})
            
            answer_formatted = markdown_to_telegram_html(answer)

            await message.reply(
                answer_formatted,
                parse_mode=ParseMode.HTML
            )

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


md = mistune.create_markdown(
    escape=False,
    plugins=[
        "strikethrough",
        "url"
    ]
)


def markdown_to_telegram_html(text: str) -> str:
    html = md(text)

    html = re.sub(r"<p>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL)

    html = re.sub(
        r'<pre><code(?: class="language-(.*?))?">(.*?)</code></pre>',
        lambda m: (
            f'<pre>{m.group(2)}</pre>'
        ),
        html,
        flags=re.DOTALL
    )

    return html.strip()
