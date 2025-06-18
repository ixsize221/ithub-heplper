from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from app import keyboards as kb
from app import quest_ai
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import json
import os
from datetime import datetime

router = Router()

import sqlite3
import os
from collections import Counter

def init_db():
    db_path = 'university_bot.db'
    print(f"📁 Подключение к базе данных: {os.path.abspath(db_path)}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(questions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'category' not in columns:
        print("🔄 Добавление колонки category в таблицу questions")
        cursor.execute('ALTER TABLE questions ADD COLUMN category TEXT DEFAULT "other"')
        conn.commit()
        print("✅ Колонка category успешно добавлена")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL UNIQUE,
            ask_count INTEGER DEFAULT 1,
            answer_text TEXT,
            is_common BOOLEAN DEFAULT FALSE,
            category TEXT DEFAULT 'other',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM questions')
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("📝 Добавление начальных вопросов")
        initial_questions = [
            ("Как получить справку об обучении?", "Справку можно заказать в личном кабинете университета", "education"),
            ("Где узнать расписание?", "Расписание доступно на сайте университета и в мобильном приложении.", "education"),
            ("Как подать заявку на общежитие?", "Заявку можно подать через личный кабинет студента.", "admission"),
            ("Какие документы нужны для поступления?", "Подайте заявку, заключите договор, оплатите обучение. ЕГЭ и ОГЭ не требуются. Главное требование — наличие документа об образовании (аттестат или диплом). Успешные кейсы в портфолио дают преимущество при поступлении.", "admission")
        ]
        
        for question, answer, category in initial_questions:
            try:
                cursor.execute('''
                    INSERT INTO questions (question_text, answer_text, ask_count, is_common, category)
                    VALUES (?, ?, 10, TRUE, ?)
                ''', (question, answer, category))
            except sqlite3.IntegrityError as e:
                print(f"⚠️ Ошибка вставки: {e}")
        
        conn.commit()
        print("✅ Начальные вопросы успешно добавлены")
    
    conn.close()
    print("✅ Инициализация базы данных завершена")

init_db()

class QuestionForm(StatesGroup):
    waiting_for_question = State()
    waiting_for_custom_question = State()

def analyze_question(question: str) -> str:
    """Анализ вопроса и определение его категории"""
    question = question.lower()
    
    keywords = {
        "admission": ["поступление", "поступить", "приемная", "комиссия", "документы", "экзамены"],
        "education": ["обучение", "учеба", "занятия", "расписание", "сессия", "экзамены"],
        "specialties": ["специальность", "направление", "профессия", "разработка", "программирование"]
    }
    
    for category, words in keywords.items():
        if any(word in question for word in words):
            return category
    
    return "other"

def add_question_to_db(question: str, answer: str = None):
    """Добавление вопроса в базу данных"""
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    try:

        cursor.execute('''
            INSERT INTO questions (question_text, answer_text, category)
            VALUES (?, ?, ?)
        ''', (question, answer, analyze_question(question)))
    except sqlite3.IntegrityError:
        cursor.execute('''
            UPDATE questions 
            SET ask_count = ask_count + 1
            WHERE question_text = ?
        ''', (question,))
    
    conn.commit()
    conn.close()

def get_popular_questions(limit=5, category=None):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    if category:
        cursor.execute('''
            SELECT question_text, answer_text 
            FROM questions 
            WHERE category = ?
            ORDER BY ask_count DESC
            LIMIT ?
        ''', (category, limit))
    else:
        cursor.execute('''
            SELECT question_text, answer_text 
            FROM questions 
            ORDER BY ask_count DESC
            LIMIT ?
        ''', (limit,))
    
    questions = cursor.fetchall()
    conn.close()
    return questions

def get_category_stats():
    """Получение статистики по категориям"""
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT category, COUNT(*) as count
        FROM questions
        GROUP BY category
    ''')
    
    stats = dict(cursor.fetchall())
    conn.close()
    return stats

def increment_question_count(question_text):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE questions 
        SET ask_count = ask_count + 1
        WHERE question_text = ?
    ''', (question_text,))
    conn.commit()
    conn.close()

@router.callback_query(F.data.startswith("popular_"))
async def show_pop(callback: CallbackQuery):
    index = int(callback.data.split("_")[1]) - 1
    popular_questions = get_popular_questions()
    
    if index < len(popular_questions):
        question, answer = popular_questions[index]
        increment_question_count(question)
        await callback.message.answer(f"❓ {question}\n\n💬 {answer}")
    else:
        await callback.message.answer("⚠️ Вопрос не найден.")
        
class AnswerForm(StatesGroup):
    waiting_for_reply = State()

class GPTForm(StatesGroup):
    text = State()

rektor_id = 7844311755

questions = {}

@router.message(CommandStart())
async def start_bot(message: types.Message):
    await message.answer(
    "👋 Привет! Я — бот, который с радостью поможет тебе найти ответ на любой интересующий вопрос 😊\n\n"
    "👇 Просто выбери одну из кнопок ниже, и мы начнём наше общение!", 
    reply_markup=await kb.main_kb())

@router.callback_query(F.data == 'quest1')
async def step_ai(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text('впиши свой вопрос нейросети\nНапример: Какие документы нужны для поступления в ДГТУ?')
    await state.set_state(GPTForm.text)

@router.message(F.text, GPTForm.text)
async def main_GPT(message: types.Message, state: FSMContext):
    status = await message.answer('Генерация ответа...')
    text = await quest_ai.ask_gpt(prompt=message.text)
    
    # Добавляем вопрос и ответ в базу данных
    add_question_to_db(message.text, text)
    
    await status.edit_text(f'{text}')
    await state.clear()

@router.callback_query(F.data == "quests")
async def main_cmd(call: CallbackQuery):
    # Получаем статистику по категориям
    stats = get_category_stats()
    
    keyboard_buttons = []
    keyboard_buttons.append([InlineKeyboardButton(text='Задать вопрос нейросети', callback_data='quest1')])
    

    categories = {
        "admission": "📚 Поступление",
        "education": "🎓 Обучение",
        "specialties": "💼 Специальности",
        "other": "❓ Прочее"
    }
    
    for category, title in categories.items():
        if category in stats and stats[category] > 0:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{title} ({stats[category]})",
                callback_data=f"category_{category}"
            )])
    
    keyboard_buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='back_to_main')])
    popular_questions_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await call.message.edit_text('Выбери категорию вопросов или задай свой вопрос:', reply_markup=popular_questions_markup)

@router.callback_query(F.data.startswith("category_"))
async def show_category_questions(callback: CallbackQuery):
    category = callback.data.replace("category_", "")
    questions = get_popular_questions(limit=5, category=category)
    
    keyboard_buttons = []
    for i, (question_text, _) in enumerate(questions):
        keyboard_buttons.append([InlineKeyboardButton(
            text=question_text,
            callback_data=f'popular_{i+1}'
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='quests')])
    questions_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    category_titles = {
        "admission": "📚 Вопросы о поступлении",
        "education": "🎓 Вопросы об обучении",
        "specialties": "💼 Вопросы о специальностях",
        "other": "❓ Прочие вопросы"
    }
    
    await callback.message.edit_text(
        f"{category_titles.get(category, 'Вопросы')}:",
        reply_markup=questions_markup
    )

@router.callback_query(F.data == 'back_to_main')
async def back_to_main_menu(call: CallbackQuery):
    await call.message.edit_text(
        "👋 Привет! Я — бот, который с радостью поможет тебе найти ответ на любой интересующий вопрос 😊\n\n"\
        "👇 Просто выбери одну из кнопок ниже, и мы начнём наше общение!", 
        reply_markup=await kb.main_kb()
    )

@router.callback_query(F.data == 'anon')
async def text_anon(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Впиши свой вопрос')
    await state.set_state(QuestionForm.waiting_for_question)

@router.message(QuestionForm.waiting_for_question)
async def receive_question(message: types.Message, state: FSMContext):
    question = message.text
    user_id = message.from_user.id
    
    add_question_to_db(question)
    
    await message.bot.send_message(
        chat_id=rektor_id,
        text=f"📩 Анонимный вопрос от студента:\n\n{question}",
        reply_markup=await kb.answer_quest(user_id)
    )
    
    await message.answer('✅ Ваш вопрос был отправлен ректору. Спасибо! ')
    await state.clear()

@router.callback_query(F.data.startswith("answer_"))
async def answer_question(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    await callback.message.answer("Введите ваш ответ на вопрос:")
    await state.set_state(AnswerForm.waiting_for_reply)
    await state.update_data(user_id=user_id)

@router.message(AnswerForm.waiting_for_reply)
async def receive_answer(message: types.Message, state: FSMContext):
    answer = message.text
    data = await state.get_data()
    question_id = data['user_id']
    
    await message.bot.send_message(
        chat_id=question_id,
        text=f"📬 Ответ на ваш вопрос:\n\n{answer}"
    )
    
    await message.answer("✅ Ответ успешно отправлен пользователю!")
    await state.clear()

    
    

    
