import logging, asyncio, os, sqlite3, config, texts, re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.utils.exceptions import ChatNotFound
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentTypes

# ——————— ЛОГИРОВАНИЕ ———————

logging.basicConfig(level=logging.INFO)

# —————— ИНТАЛИЗАЦИЯ БОТА——————

bot = Bot(token=config.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ——————— БАЗА ДАННЫХ ———————

conn = sqlite3.connect('dataBase.sqlite')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER
    )
''')

conn.commit()


# ——— ФУНКЦИИ, КЛАССЫ, СТЕЙТЫ ———


def uids():
    rows = c.execute("SELECT id FROM users").fetchall()
    c.execute("SELECT * FROM users")
    countr = int(len(c.fetchall()))
    print(countr)
    return (countr)
    for i in range(countr):
        print(rows[i][0])
    conn.commit()


class states(StatesGroup):
    getmsg_feedback = State()
    getmsg_alert = State()
    sendmsg_alert = State()


# ——————— ОСНОВА ———————

@dp.message_handler(Command("start"))
async def start(message: types.Message):
    c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    conn.commit()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(texts.info_button, callback_data="info"),
        InlineKeyboardButton(texts.feedback_button, callback_data="feedback")
    )

    await message.answer(texts.start_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'back')
async def back_to_menu(cq: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(texts.info_button, callback_data="info"),
        InlineKeyboardButton(texts.feedback_button, callback_data="feedback")
    )

    await cq.message.edit_text(texts.start_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'info')
async def info(cq: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙", callback_data="back"))

    await cq.message.edit_text(texts.info_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'feedback')
async def info(cq: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙", callback_data="back"))

    await cq.message.edit_text(texts.feedback_request, reply_markup=keyboard)
    await states.getmsg_feedback.set()


@dp.message_handler(state=states.getmsg_feedback, content_types=ContentTypes.ANY)
async def get_msg(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙", callback_data="back"))

    await bot.send_message(chat_id=config.group_id, text=f"<b>Сообщение от {message.from_user.get_mention(as_html=True)}</b>\nID - {message.from_user.id}\n\n👇👇👇", parse_mode="HTML")
    await bot.copy_message(chat_id=config.group_id, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.reply("✅ Успешно отправлено", reply_markup=keyboard)
    await state.finish()

@dp.message_handler(chat_id=config.group_id)
async def answer(message: types.Message):
    if not message.reply_to_message.text:
        return

    pattern = re.compile(r'ID\s*-\s*(\d+)')
    match = pattern.search(message.reply_to_message.text)

    if match:
        id = match.group(1)
        await bot.send_message(chat_id=id, text=f"""
Ответ на ваш вопрос:
{message.text}
        """)
    else:
        return

@dp.message_handler(commands=['alert'])
async def sends(message):
    if message.forward_sender_name is not None:
        await message.answer('ты не админ)')
    else:
        await bot.send_message(message.from_user.id, 'Введите пароль:')
        uids()
        await states.getmsg_alert.set()


@dp.message_handler(state=states.getmsg_alert)
async def st2(message: types.Message, state: FSMContext):
    passwd = message.text
    if passwd == config.password:
        if message.from_user.id in config.admins_ids:
            await bot.send_message(message.from_user.id, 'Введите сообщение')
            await states.sendmsg_alert.set()
        else:
            await bot.send_message(message.from_user.id, 'Ошибка!')
            await state.finish()
    else:
        await bot.send_message(message.from_user.id, 'Ошибка!')
        await state.finish()


@dp.message_handler(state=states.sendmsg_alert)
async def st2(message: types.Message, state: FSMContext):
    rasstxt = message.text
    if rasstxt == 'q':
        await bot.send_message(message.from_user.id, 'Отмена')
        await state.finish()
    elif rasstxt == 'й':
        await bot.send_message(message.from_user.id, 'Отмена')
        await state.finish()
    else:
        fail = 0
        suc = 0
        f = open(f"alert.txt", 'w')
        for id in config.admins_ids:
            await bot.send_message(id, f'Через 10 секунд всем пользователям будет отправлено сообщение \n \n{rasstxt}')
        await asyncio.sleep(10)
        for id in config.admins_ids:
            await bot.copy_message(id, f'Началась рассылка. Текст: \n \n{rasstxt}')
        rows = c.execute("SELECT id FROM users").fetchall()
        c.execute("SELECT * FROM users")
        countr = int(len(c.fetchall()))
        for i in range(countr):
            try:
                await bot.copy_message(chat_id=rows[i][0], from_chat_id=message.chat.id, message_id=message.message_id)
                f.write(f'{rows[i][0]} сообщение отправлено\n')
                suc = suc + 1
            except ChatNotFound:
                fail = fail + 1
                uban = str(rows[i][0]) + ' добавил бота в чс и был удален\n'
                f.write(uban)
        f.write(f'\n \n \nУдачных отправок: {suc}\nНеудачных отправок: {fail}')
        f.close()
        for id in config.admins_ids:
            await bot.send_document(id, open(f"alert.txt", 'rb'), caption=f'Отчет по рассылке.')
        os.remove(f"alert.txt")
        await state.finish()


if __name__ == '__main__':
    logging.info("Bot started")
    executor.start_polling(dp, skip_updates=True)
