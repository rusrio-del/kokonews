from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8636589473:AAHyTHh1G8GB-xVtlLrx6YLe0VjekXd5fl8"
ADMIN_ID = 1044750995
CHANNEL_ID = -1003743890998

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

pending = {}

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Отправь новость одним сообщением. Анонимно.")

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def get_news(message: types.Message):
    pid = message.message_id
    pending[pid] = message.text

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Опубликовать", callback_data=f"ok:{pid}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"no:{pid}")
    )

    await bot.send_message(
        ADMIN_ID,
        f"🆕 Новость:\n\n{message.text}",
        reply_markup=kb
    )

    await message.answer("Новость отправлена на модерацию")

@dp.callback_query_handler(lambda c: c.data.startswith("ok"))
async def approve(c: types.CallbackQuery):
    pid = int(c.data.split(":")[1])
    await bot.send_message(CHANNEL_ID, pending[pid])
    await c.message.edit_text("✅ Опубликовано")
    pending.pop(pid, None)

@dp.callback_query_handler(lambda c: c.data.startswith("no"))
async def reject(c: types.CallbackQuery):
    pid = int(c.data.split(":")[1])
    pending.pop(pid, None)
    await c.message.edit_text("❌ Отклонено")

if __name__ == "__main__":
    executor.start_polling(dp)
