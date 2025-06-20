import g4f
import asyncio
import aiohttp
import re
import json
import os
from typing import List, Dict
from datetime import datetime
from collections import Counter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# Константы для работы с сайтом
ITHUB_URL = "https://rostov.ithub.ru/"
SPECIALTIES = {
    "Разработка": ["Бэкенд-разработчик", "Фронтенд-разработчик"],
    "Программирование": ["Дата-инженер", "Java-разработчик", "NET-разработчик"],
    "Управление ИТ продуктом": ["Менеджер ИТ-проектов"]
}

def format_specialties(specialties: Dict[str, List[str]]) -> str:
    """Форматирование информации о специальностях"""
    result = []
    for category, roles in specialties.items():
        result.append(f"{category}:")
        for role in roles:
            result.append(f"- {role}")
    return "\n".join(result)

def format_features(features: List[str]) -> str:
    """Форматирование особенностей обучения"""
    return "\n".join(f"- {feature}" for feature in features)

async def fetch_ithub_content() -> Dict[str, str]:
    """Получение контента с сайта ITHub"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ITHUB_URL) as response:
                if response.status == 200:
                    html = await response.text()
                    return {
                        "about": "ITHub - это колледж информационных технологий при ДГТУ",
                        "specialties": SPECIALTIES,
                        "features": [
                            "Современные образовательные программы",
                            "Практико-ориентированное обучение",
                            "Сотрудничество с IT-компаниями"
                        ],
                        "education": "Обучение ведется по программам среднего профессионального образования",
                        "admission": "Прием документов осуществляется в соответствии с правилами приема",
                        "contacts": "Телефон: +7 (863) 123-45-67, Email: info@ithub.ru"
                    }
    except Exception as e:
        print(f"Ошибка при получении контента с сайта: {str(e)}")
        return {}

def sync_gpt_request(prompt: str, context: Dict[str, str], model: str = 'gpt-4') -> str:
    try:
        system_message = f"""Вы - помощник колледжа информационных технологий ITHub при ДГТУ. 
        Используйте ТОЛЬКО следующую информацию для ответов:

        О колледже: {context.get('about', '')}
        
        Специальности и роли:
        {format_specialties(context.get('specialties', {}))}
        
        Особенности обучения:
        {format_features(context.get('features', []))}
        
        Образование: {context.get('education', '')}
        
        Поступление: {context.get('admission', '')}
        
        Контакты: {context.get('contacts', '')}

        Правила ответов:
        1. Отвечайте ТОЛЬКО на основе предоставленной информации
        2. Если информации нет в контексте, скажите "я нихуя незнаю, съеби нахуй черт."
        3. Отвечайте кратко и по существу
        4. Если вопрос не связан с колледжем, обматери жестко  человека и сообщите об этом в грубой форме обязательно с матами
        5. Адрес главного корпусв : Ростов-на-Дону, пл. Гагарина, д. 1
        """
        
    
        response = g4f.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        return response
    except Exception as e:
        return f"Ошибка: {str(e)}"
        

async def ask_gpt(prompt: str, model: str = 'gpt-4') -> str:

    context = await fetch_ithub_content()
    
    return await asyncio.to_thread(sync_gpt_request, prompt, context, model)

gpt_key = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text='Назад', callback_data='back')
]])



