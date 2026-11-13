import logging
import tempfile
import time
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.interfaces import KnowledgeBase

logger = logging.getLogger(__name__)
router = Router()

web_enabled: set[int] = set()    # у кого включён веб-поиск
awaiting_file: set[int] = set()  # кто сейчас должен прислать файл после /rag

START_TEXT = (
    "👋 Привет! Я AI-агент: сам решаю, когда искать в ваших документах, "
    "в интернете или считать.\n\n"
    "/ask <вопрос> — задать вопрос (можно писать просто текстом)\n"
    "/parse — включить или выключить веб-поиск\n"
    "/rag — загрузить документ (.txt, .md, .pdf)"
)


def _tools_used(messages: list) -> list[str]:
    """Имена инструментов, вызванных в текущем ходе (после последнего сообщения пользователя)."""
    used = []
    for message in reversed(messages):
        if message.type == "human":
            break
        if message.type == "tool":
            used.append(message.name)
    return list(reversed(used))


@router.message(CommandStart())
async def start(message: Message, agent) -> None:
    user_id = message.from_user.id
    await agent.checkpointer.adelete_thread(str(user_id))
    logger.info("/start user=%s (history reset)", user_id)
    await message.answer(START_TEXT)


@router.message(Command("ask"))
async def ask_command(message: Message, command: CommandObject, bot: Bot, agent) -> None:
    if not command.args:
        await message.answer("⚠️ После /ask нужно написать вопрос.")
        return
    await answer_question(message, bot, agent, command.args)


@router.message(F.text & ~F.text.startswith("/"))
async def ask_text(message: Message, bot: Bot, agent) -> None:
    await answer_question(message, bot, agent, message.text)


async def answer_question(message: Message, bot: Bot, agent, text: str) -> None:
    user_id = message.from_user.id
    web = user_id in web_enabled
    config = {
        "configurable": {"thread_id": str(user_id), "user_id": user_id, "web": web},
        "recursion_limit": 12,
    }
    logger.info("question user=%s web=%s len=%d", user_id, web, len(text))

    started = time.perf_counter()
    try:
        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            result = await agent.ainvoke({"messages": [("user", text)]}, config)
    except Exception:
        logger.exception("agent failed user=%s", user_id)
        await message.answer("⚠️ Не удалось получить ответ, попробуйте ещё раз.")
        return

    answer = result["messages"][-1].content
    logger.info(
        "answer user=%s tools=%s time=%.2fs len=%d",
        user_id, _tools_used(result["messages"]), time.perf_counter() - started, len(answer),
    )
    await message.answer(answer[:4000])


@router.message(Command("parse"))
async def parse(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Включить", callback_data="parse:on")
    kb.button(text="❌ Выключить", callback_data="parse:off")
    status = "включён" if message.from_user.id in web_enabled else "выключен"
    await message.answer(f"⚙️ Веб-поиск сейчас {status}.", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("parse:"))
async def parse_toggle(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if callback.data == "parse:on":
        web_enabled.add(user_id)
        text = "✅ Веб-поиск включён."
    else:
        web_enabled.discard(user_id)
        text = "❌ Веб-поиск выключен."
    logger.info("web search user=%s enabled=%s", user_id, user_id in web_enabled)
    await callback.answer()
    await callback.message.edit_text(text)


@router.message(Command("rag"))
async def rag(message: Message) -> None:
    awaiting_file.add(message.from_user.id)
    logger.info("/rag user=%s waiting for file", message.from_user.id)
    await message.answer("📂 Отправьте .txt, .md или .pdf файл.")


@router.message(F.document)
async def document(message: Message, bot: Bot, kb: KnowledgeBase) -> None:
    user_id = message.from_user.id
    if user_id not in awaiting_file:
        await message.answer("ℹ️ Сначала используйте команду /rag.")
        return

    name = Path(message.document.file_name or "document").name
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            await bot.download(message.document, destination=path)
            count = await kb.add_file(user_id, path, name)
    except ValueError:
        logger.warning("unsupported file user=%s name=%s", user_id, name)
        await message.answer("⚠️ Формат не поддерживается.")
        return
    except Exception:
        logger.exception("ingest failed user=%s name=%s", user_id, name)
        await message.answer("⚠️ Ошибка при обработке файла.")
        return

    awaiting_file.discard(user_id)
    logger.info(
        "file added user=%s name=%s chunks=%d time=%.2fs",
        user_id, name, count, time.perf_counter() - started,
    )
    await message.answer(f"✅ «{name}» добавлен в базу ({count} фрагментов).")