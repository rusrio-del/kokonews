import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === ВСТАВЬ СВОИ ДАННЫЕ ===
API_TOKEN = 8636589473:AAHyTHh1G8GB-xVtlLrx6YLe0VjekXd5fl8
ADMIN_ID = 1044750995
CHANNEL_ID = --1003743890998
# =========================

pending = {}

def make_kb(pid: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Опубликовать", callback_data=f"ok:{pid}")
    kb.button(text="❌ Отклонить", callback_data=f"no:{pid}")
    kb.adjust(2)
    return kb.as_markup()

def admin_caption(prefix: str, caption: str) -> str:
    caption = (caption or "").strip()
    return f"{prefix}\n\n{caption}" if caption else prefix

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    @dp.message(F.text.startswith("/start"))
    async def start(message: Message):
        await message.answer(
            "📨 Отправь новость одним сообщением.\n"
            "Поддерживается: текст, фото, видео, документы (pdf/zip и т.д.), голосовые,\n"
            "и альбомы (несколько фото/видео за раз).\n"
            "Анонимно."
        )

    # ========= АЛЬБОМЫ (MEDIA GROUP) =========
    # Важный момент: Telegram присылает элементы альбома отдельными сообщениями,
    # поэтому мы собираем их в память и через короткую паузу отправляем как 1 заявку.
    media_groups = {}  # key: media_group_id -> {"chat_id": int, "items": [], "caption": str, "task": asyncio.Task}

    async def flush_media_group(group_id: str):
        # ждём, пока Telegram досыплет элементы альбома
        await asyncio.sleep(1.2)

        group = media_groups.pop(group_id, None)
        if not group:
            return

        pid = group["pid"]
        items = group["items"]
        caption = group["caption"]

        pending[pid] = {
            "type": "album",
            "items": items,        # list of {"kind": "photo"/"video", "file_id": "..."}
            "caption": caption
        }

        # отправляем админу: сначала заголовок + кнопки, потом сами медиа
        await bot.send_message(
            ADMIN_ID,
            admin_caption("🆕 Новость (альбом):", caption),
            reply_markup=make_kb(pid)
        )

        # отправляем медиа по одному (надёжно), чтобы точно дошло везде
        for i, it in enumerate(items, start=1):
            if it["kind"] == "photo":
                await bot.send_photo(ADMIN_ID, it["file_id"], caption=f"#{i}/{len(items)}")
            else:
                await bot.send_video(ADMIN_ID, it["file_id"], caption=f"#{i}/{len(items)}")

    @dp.message(F.media_group_id)
    async def handle_media_group(message: Message):
        gid = str(message.media_group_id)

        # берём файл
        if message.photo:
            file_id = message.photo[-1].file_id
            kind = "photo"
        elif message.video:
            file_id = message.video.file_id
            kind = "video"
        else:
            # редкий кейс: альбом может быть другим типом — игнорируем
            return

        if gid not in media_groups:
            # pid берём по первому сообщению группы
            media_groups[gid] = {
                "pid": message.message_id,
                "items": [],
                "caption": message.caption or "",
                "task": None
            }

        media_groups[gid]["items"].append({"kind": kind, "file_id": file_id})

        # если пользователь добавил подпись НЕ в первом элементе — обновим подпись
        if message.caption:
            media_groups[gid]["caption"] = message.caption

        # перезапускаем таймер “сборки”
        task = media_groups[gid].get("task")
        if task and not task.done():
            task.cancel()
        media_groups[gid]["task"] = asyncio.create_task(flush_media_group(gid))

        await message.answer("✅ Альбом принят. Отправляю на модерацию…")

    # ========= ТЕКСТ =========
    @dp.message(F.text)
    async def handle_text(message: Message):
        pid = message.message_id
        pending[pid] = {"type": "text", "text": message.text}

        await bot.send_message(
            ADMIN_ID,
            f"🆕 Новость (текст):\n\n{message.text}",
            reply_markup=make_kb(pid)
        )
        await message.answer("✅ Новость отправлена на модерацию")

    # ========= ФОТО (одиночное, НЕ альбом) =========
    @dp.message(F.photo & ~F.media_group_id)
    async def handle_photo(message: Message):
        pid = message.message_id
        file_id = message.photo[-1].file_id
        caption = message.caption or ""

        pending[pid] = {"type": "photo", "file_id": file_id, "caption": caption}

        await bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=admin_caption("🆕 Новость (фото):", caption),
            reply_markup=make_kb(pid)
        )
        await message.answer("✅ Фото отправлено на модерацию")

    # ========= ВИДЕО (одиночное, НЕ альбом) =========
    @dp.message(F.video & ~F.media_group_id)
    async def handle_video(message: Message):
        pid = message.message_id
        file_id = message.video.file_id
        caption = message.caption or ""

        pending[pid] = {"type": "video", "file_id": file_id, "caption": caption}

        await bot.send_video(
            ADMIN_ID,
            file_id,
            caption=admin_caption("🆕 Новость (видео):", caption),
            reply_markup=make_kb(pid)
        )
        await message.answer("✅ Видео отправлено на модерацию")

    # ========= ДОКУМЕНТЫ (pdf/zip/любые файлы) =========
    @dp.message(F.document)
    async def handle_document(message: Message):
        pid = message.message_id
        doc = message.document
        caption = message.caption or ""

        pending[pid] = {
            "type": "document",
            "file_id": doc.file_id,
            "filename": doc.file_name,
            "caption": caption
        }

        await bot.send_document(
            ADMIN_ID,
            doc.file_id,
            caption=admin_caption(f"🆕 Новость (файл): {doc.file_name}", caption),
            reply_markup=make_kb(pid)
        )
        await message.answer("✅ Файл отправлен на модерацию")

    # ========= ГОЛОСОВЫЕ (voice) =========
    @dp.message(F.voice)
    async def handle_voice(message: Message):
        pid = message.message_id
        v = message.voice
        caption = message.caption or ""

        pending[pid] = {
            "type": "voice",
            "file_id": v.file_id,
            "caption": caption
        }

        await bot.send_voice(
            ADMIN_ID,
            v.file_id,
            caption=admin_caption("🆕 Новость (голосовое):", caption),
            reply_markup=make_kb(pid)
        )
        await message.answer("✅ Голосовое отправлено на модерацию")

    # ========= ПОДТВЕРДИТЬ =========
    @dp.callback_query(F.data.startswith("ok:"))
    async def approve(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        item = pending.pop(pid, None)

        if not item:
            await c.answer("Уже обработано", show_alert=False)
            return

        t = item["type"]

        if t == "text":
            await bot.send_message(CHANNEL_ID, item["text"])

        elif t == "photo":
            await bot.send_photo(CHANNEL_ID, item["file_id"], caption=item["caption"])

        elif t == "video":
            await bot.send_video(CHANNEL_ID, item["file_id"], caption=item["caption"])

        elif t == "document":
            await bot.send_document(
                CHANNEL_ID,
                item["file_id"],
                caption=item["caption"] or item.get("filename", "")
            )

        elif t == "voice":
            # голосовые в каналы отлично отправляются как voice
            await bot.send_voice(CHANNEL_ID, item["file_id"], caption=item["caption"])

        elif t == "album":
            # отправим в канал “пачкой” (по одному, надёжно)
            cap = item.get("caption", "")
            if cap:
                await bot.send_message(CHANNEL_ID, cap)
            for it in item["items"]:
                if it["kind"] == "photo":
                    await bot.send_photo(CHANNEL_ID, it["file_id"])
                else:
                    await bot.send_video(CHANNEL_ID, it["file_id"])

        # отметим в сообщении админа
        if c.message.caption:
            await c.message.edit_caption("✅ Опубликовано")
        else:
            await c.message.edit_text("✅ Опубликовано")
        await c.answer()

    # ========= ОТКЛОНИТЬ =========
    @dp.callback_query(F.data.startswith("no:"))
    async def reject(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        pending.pop(pid, None)

        if c.message.caption:
            await c.message.edit_caption("❌ Отклонено")
        else:
            await c.message.edit_text("❌ Отклонено")
        await c.answer()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
