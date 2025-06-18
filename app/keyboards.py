from aiogram.types import InlineKeyboardMarkup as kb_markup
from aiogram.types import InlineKeyboardButton as kb_button

async def main_kb():
    keyboard =  kb_markup(inline_keyboard=[[
        kb_button(text="Ответы на популярные вопросы📰", callback_data="quests"),
    ],[
        kb_button(text= "Отправить анонимный вопрос Ректору🏫", callback_data= "anon")
    ]])
    return keyboard

async def answer_quest(user_id: int):
    reply_markup = kb_markup(inline_keyboard=[[
        kb_button(
            text="Ответить",
            callback_data=f"answer_{user_id}"
        )
    ]])
    return reply_markup