import asyncio
import sqlite3
from collections.abc import Callable
from typing import Any

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import GeoRule

from city_store import get_city, set_city
from config import state_dispenser
from keyboards import (
    AIR_BUTTON,
    CANCEL_BUTTON,
    CITY_BUTTON,
    FIVE_DAY_BUTTON,
    TODAY_BUTTON,
    get_cancel_keyboard,
    get_main_menu_keyboard,
)
from states import WeatherState
from weather_service import (
    WeatherError,
    format_air_quality,
    format_current_weather,
    format_five_day_forecast,
    get_air_quality,
    get_city_by_coordinates,
    get_current_weather,
    get_five_day_forecast,
    get_weather_by_coordinates,
    validate_city,
)

weather_labeler = BotLabeler()

WeatherFetcher = Callable[[str], dict[str, Any]]
WeatherFormatter = Callable[[str, dict[str, Any]], str]

WEATHER_ACTIONS: dict[str, str] = {
    TODAY_BUTTON: "today",
    FIVE_DAY_BUTTON: "five_day",
    AIR_BUTTON: "air",
}
WEATHER_FETCHERS: dict[str, WeatherFetcher] = {
    "today": get_current_weather,
    "five_day": get_five_day_forecast,
    "air": get_air_quality,
}
WEATHER_FORMATTERS: dict[str, WeatherFormatter] = {
    "today": format_current_weather,
    "five_day": format_five_day_forecast,
    "air": format_air_quality,
}
START_WORDS = ["start", "начать", "начало", "главное меню", "меню"]


@weather_labeler.private_message(text=list(START_WORDS))
async def cmd_start(message: Message):
    await state_dispenser.delete(message.peer_id)
    await message.answer(
        "👋 Привет! Я помогу узнать погоду и качество воздуха.\n"
        "Выберите, что показать:",
        keyboard=get_main_menu_keyboard(),
    )


@weather_labeler.private_message(text=list(WEATHER_ACTIONS))
async def select_weather(message: Message):
    action = WEATHER_ACTIONS[message.text]
    try:
        city = await asyncio.to_thread(get_city, message.from_id)
    except sqlite3.Error:
        await message.answer(
            "Не удалось прочитать сохранённый город. Попробуйте ещё раз позже."
        )
        return

    if not city:
        await message.answer(
            "Сначала выберите город кнопкой «🏙 Выбрать город», "
            "затем повторите запрос.",
            keyboard=get_main_menu_keyboard(),
        )
        return

    try:
        payload = await asyncio.to_thread(WEATHER_FETCHERS[action], city)
        result = await asyncio.to_thread(WEATHER_FORMATTERS[action], city, payload)
    except WeatherError as exc:
        result = str(exc)
    await message.answer(result, keyboard=get_main_menu_keyboard())


@weather_labeler.private_message(text=CITY_BUTTON)
async def select_city(message: Message):
    await state_dispenser.set(message.peer_id, WeatherState.city)
    await message.answer(
        "Введите название города (например, Москва) "
        "или отправьте геопозицию из меню вложений VK:",
        keyboard=get_cancel_keyboard(),
    )


@weather_labeler.private_message(GeoRule())
async def process_geolocation(message: Message):
    coordinates = message.geo.coordinates if message.geo else None
    if not coordinates:
        await message.answer(
            "В сообщении не удалось прочитать координаты. "
            "Отправьте геопозицию ещё раз."
        )
        return

    try:
        lat = coordinates.latitude
        lon = coordinates.longitude
        weather = await asyncio.to_thread(
            get_weather_by_coordinates,
            lat,
            lon,
        )
    except WeatherError as exc:
        await message.answer(
            str(exc),
            keyboard=get_main_menu_keyboard(),
        )
        return

    city = None
    location_note = ""
    try:
        city = await asyncio.to_thread(
            get_city_by_coordinates,
            lat,
            lon,
        )
        await asyncio.to_thread(set_city, message.from_id, city)
    except WeatherError as exc:
        location_note = f"\nНе удалось определить название города: {exc}"
    except sqlite3.Error:
        location_note = "\nНе удалось сохранить город для следующих запросов."

    location = city or weather.get("name") or f"{lat:.4f}, {lon:.4f}"
    result = await asyncio.to_thread(format_current_weather, location, weather)
    await state_dispenser.delete(message.peer_id)
    await message.answer(
        f"{result}{location_note}",
        keyboard=get_main_menu_keyboard(),
    )


@weather_labeler.private_message(state=WeatherState.city)
async def process_city(message: Message):
    if message.text.strip().casefold() in {CANCEL_BUTTON.casefold(), "отмена"}:
        await state_dispenser.delete(message.peer_id)
        await message.answer(
            "Запрос отменён. Выберите следующий запрос:",
            keyboard=get_main_menu_keyboard(),
        )
        return

    city = message.text.strip()
    if not city:
        await message.answer("Введите название города или нажмите «❌ Отмена».")
        return

    try:
        city = await asyncio.to_thread(validate_city, city)
        await asyncio.to_thread(set_city, message.from_id, city)
    except WeatherError as exc:
        await message.answer(
            f"{exc}\nВведите другой город, отправьте геопозицию "
            "или нажмите «❌ Отмена».",
            keyboard=get_cancel_keyboard(),
        )
        return
    except sqlite3.Error:
        await state_dispenser.delete(message.peer_id)
        await message.answer(
            "Не удалось сохранить город. Попробуйте ещё раз позже.",
            keyboard=get_main_menu_keyboard(),
        )
        return

    await state_dispenser.delete(message.peer_id)
    await message.answer(
        f"Город «{city}» сохранён. Теперь запросы погоды будут использовать его.",
        keyboard=get_main_menu_keyboard(),
    )


@weather_labeler.private_message()
async def show_menu_for_unrecognized_message(message: Message):
    await message.answer(
        "Чтобы открыть меню, выберите одну из кнопок ниже. "
        "Сначала задайте город кнопкой «🏙 Выбрать город».",
        keyboard=get_main_menu_keyboard(),
    )
