from vkbottle import Bot

from config import VK_TOKEN, api, labeler, state_dispenser
from handlers import weather_labeler

labeler.load(weather_labeler)

bot = Bot(
    api=api,
    labeler=labeler,
    state_dispenser=state_dispenser,
)

if __name__ == "__main__":
    if not VK_TOKEN:
        raise SystemExit("Не задан VK_TOKEN. Добавьте токен сообщества в файл .env.")
    print("Бот погоды запущен. Для остановки нажмите Ctrl+C.", flush=True)
    bot.run()
