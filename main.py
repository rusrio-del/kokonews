import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart

# ==========================
# 🔴 ЗАМЕНИ ЭТИ ЗНАЧЕНИЯ
# ==========================

API_TOKEN = "8636589473:AAHyTHh1G8GB-xVtlLrx6YLe0VjekXd5fl8"
ADMIN_ID = 1044750995
CHANNEL_ID = -1003743890998

# ==========================

pending = {}

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # На всякий случай убираем webhook
    await bot.delete_webhook(drop_pending_updates=True)

    # /start
    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "🗞 Отправь новость одним сообщением.\n"
            "Она будет отправлена на модерацию анонимно."
        )

    # Любой текст, КРОМЕ команд
    @dp.message(F.text & ~F.text.startswith("/"))
    async def get_news(message: Message):
        pid = message.message_id
        pending[pid] = message.text

        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Опубликовать", callback_data=f"ok:{pid}")
        kb.button(text="❌ Отклонить", callback_data=f"no:{pid}")
        kb.adjust(2)

        await bot.send_message(
            ADMIN_ID,
            f"🆕 Новость:\n\n{message.text}",
            reply_markup=kb.as_markup()
        )

        await message.answer("✅ Новость отправлена на модерацию")

    # Одобрение
    @dp.callback_query(F.data.startswith("ok:"))
    async def approve(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        text = pending.pop(pid, None)

        if text:
            await bot.send_message(CHANNEL_ID, text)
            await c.message.edit_text("✅ Опубликовано")

        await c.answer()

    # Отклонение
    @dp.callback_query(F.data.startswith("no:"))
    async def reject(c: CallbackQuery):
        pid = int(c.data.split(":")[1])
        pending.pop(pid, None)

        await c.message.edit_text("❌ Отклонено")
        await c.answer()

    print("🤖 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
