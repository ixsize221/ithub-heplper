from aiogram import Bot, Dispatcher
import asyncio
import os
from dotenv import load_dotenv
from app.handlers import router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="a",
)

load_dotenv()

token=os.getenv("Token")

async def main():
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
    

if __name__ == '__main__':
    asyncio.run(main())