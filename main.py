import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === ВСТАВЬ СВОИ ДАННЫЕ ===
API_TOKEN = "8636589473:AAHyTHh1G8GB-xVtlLrx6YLe0VjekXd5fl8"
ADMIN_ID = 1044750995
CHANNEL_ID = -1003743890998
# ==========================

pending = {}

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    @dp.message(F.text.startswith("/start"))
    async def start(message: Message):
        await message.answer("Отправь новость одним сообщением. Анонимно.")

    @dp.message(F.photo | F.video | F.text)
    async def get_news(message: Message):
        pid = message.message_id

        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Опубликовать", callback_data=f"ok:{pid}")
        kb.button(text="❌ Отклонить", callback_data=f"no:{pid}")
        kb.adjust(2)

        # сохраняем тип и данные
        item = {"type": None, "text": None, "file_id": None, "caption": None}
        if message.photo:
            item["type"] = "photo"
            item["file_id"] = message.photo[-1].file_id
            item["caption"] = message.caption or "📰 Новость (фото)"
        elif message.video:
            item["type"] = "video"
            item["file_id"] = message.video.file_id
            item["caption"] = message.caption or "📰 Новость (видео)"
        else:
            item["type"] = "text"
            item["text"] = message.text

        pending[pid] = item

        # отправляем админу на модерацию
        if item["type"] == "photo":
            await bot.send_photo(
                ADMIN_ID, item["file_id"],
                caption=f"🆕 Новость (фото):\n\n{item['caption']}",
                reply_markup=kb.as_markup()
            )
        elif item["type"] == "video":
            await bot.send_video(
                ADMIN_ID, item["file_id"],
                caption=f"🆕 Новость (видео):\n\n{item['caption']}",
                reply_markup=kb.as_markup()
            )
        else:
            await bot.send_message(
                ADMIN_ID,
                f"🆕 Новость:\n\n{item['text']}",
                reply_markup=kb.as_markup()
            )

        await message.answer("✅ Отправлено на модерацию")

    @dp.callback_query(F.data.startswith("ok:"))
    async def approve(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        item = pending.pop(pid, None)

        if not item:
            await c.answer("Не найдено", show_alert=True)
            return

        if item["type"] == "photo":
            await bot.send_photo(CHANNEL_ID, item["file_id"], caption=item["caption"])
        elif item["type"] == "video":
            await bot.send_video(CHANNEL_ID, item["file_id"], caption=item["caption"])
        else:
            await bot.send_message(CHANNEL_ID, item["text"])

        await c.message.edit_text("✅ Опубликовано")
        await c.answer()

    @dp.callback_query(F.data.startswith("no:"))
    async def reject(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        pending.pop(pid, None)
        await c.message.edit_text("❌ Отклонено")
        await c.answer()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
