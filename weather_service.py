import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

API_KEY = (os.getenv("OPENWEATHER_API_KEY") or os.getenv("API_KEY") or "").strip()

GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
REVERSE_GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/reverse"
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FIVE_DAY_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

WEEKDAYS = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
AIR_QUALITY_LABELS = {
    1: "хорошее",
    2: "удовлетворительное",
    3: "умеренное",
    4: "плохое",
    5: "очень плохое",
}


class WeatherError(Exception):
    """An expected OpenWeather or input error that can be shown to a user."""


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any] | list[Any]:
    if not API_KEY:
        raise WeatherError(
            "Не задан ключ OpenWeather. Добавьте OPENWEATHER_API_KEY в файл .env."
        )

    request_params = {**params, "appid": API_KEY}
    for attempt in range(4):
        try:
            response = requests.get(url, params=request_params, timeout=10)
        except requests.exceptions.RequestException as exc:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            raise WeatherError(
                "Не удалось подключиться к OpenWeather. Проверьте интернет-соединение."
            ) from exc

        if response.status_code in RETRYABLE_STATUSES and attempt < 3:
            time.sleep(2**attempt)
            continue
        if response.status_code != 200:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {}
            detail = (
                error_payload.get("message")
                if isinstance(error_payload, dict)
                else None
            )
            if response.status_code in (401, 403):
                raise WeatherError(
                    "OpenWeather отклонил ключ или не разрешил этот API. "
                    "Проверьте OPENWEATHER_API_KEY и доступ к нужному API."
                )
            if response.status_code == 404:
                raise WeatherError("OpenWeather не нашёл данные для этого запроса.")
            if response.status_code == 429:
                raise WeatherError(
                    "Превышен лимит запросов OpenWeather. Попробуйте позже."
                )
            if response.status_code in RETRYABLE_STATUSES:
                raise WeatherError(
                    f"OpenWeather временно недоступен (HTTP {response.status_code})."
                )
            message = f"OpenWeather вернул ошибку HTTP {response.status_code}."
            if detail:
                message = f"{message} {detail}"
            raise WeatherError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherError("OpenWeather вернул некорректный ответ.") from exc
        if not isinstance(payload, (dict, list)):
            raise WeatherError("OpenWeather вернул ответ неизвестного формата.")
        return payload

    raise WeatherError("Не удалось получить ответ от OpenWeather.")


def _get_coordinates(city: str) -> tuple[float, float]:
    city = city.strip()
    if not city:
        raise WeatherError("Название города не должно быть пустым.")

    results = _request_json(
        GEOCODING_URL,
        {"q": city, "limit": 1, "lang": "ru"},
    )
    if not isinstance(results, list) or not results:
        raise WeatherError(f"Город «{city}» не найден. Проверьте название и повторите.")

    try:
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("OpenWeather вернул некорректные координаты города.") from exc

    _validate_coordinates(lat, lon)
    return lat, lon


def _validate_coordinates(lat: float, lon: float) -> None:
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise WeatherError("Широта должна быть числом от -90 до 90.")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise WeatherError("Долгота должна быть числом от -180 до 180.")


def get_city_by_coordinates(lat: float, lon: float) -> str:
    _validate_coordinates(lat, lon)
    results = _request_json(
        REVERSE_GEOCODING_URL,
        {"lat": lat, "lon": lon, "limit": 1},
    )
    if not isinstance(results, list) or not results:
        raise WeatherError("Не удалось определить город по этой геопозиции.")

    try:
        result = results[0]
        localized_names = result.get("local_names", {})
        city = localized_names.get("ru") or result["name"]
        state = result.get("state")
        country = result.get("country")
        location_parts = [city]
        if state and state.casefold() != city.casefold():
            location_parts.append(state)
        if country:
            location_parts.append(country)
        return ", ".join(location_parts)
    except (AttributeError, KeyError, TypeError) as exc:
        raise WeatherError(
            "OpenWeather вернул некорректный результат геокодирования."
        ) from exc


def validate_city(city: str) -> str:
    _get_coordinates(city)
    return city.strip()


def _city_weather(
    city: str,
    endpoint: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    lat, lon = _get_coordinates(city)
    params = {"lat": lat, "lon": lon, "lang": "ru"}
    if extra_params:
        params.update(extra_params)
    return _request_json(endpoint, params)


def get_current_weather(city: str) -> dict[str, Any]:
    payload = _city_weather(
        city, CURRENT_WEATHER_URL, {"units": "metric"}
    )
    if not isinstance(payload, dict):
        raise WeatherError("OpenWeather вернул некорректные данные о погоде.")
    return payload


def get_weather_by_coordinates(lat: float, lon: float) -> dict[str, Any]:
    _validate_coordinates(lat, lon)
    payload = _request_json(
        CURRENT_WEATHER_URL,
        {"lat": lat, "lon": lon, "units": "metric", "lang": "ru"},
    )
    if not isinstance(payload, dict):
        raise WeatherError("OpenWeather вернул некорректные данные о погоде.")
    return payload


def get_five_day_forecast(city: str) -> dict[str, Any]:
    payload = _city_weather(
        city,
        FIVE_DAY_FORECAST_URL,
        {"units": "metric"},
    )
    if not isinstance(payload, dict):
        raise WeatherError("OpenWeather вернул некорректный прогноз погоды.")
    return payload


def get_air_quality(city: str) -> dict[str, Any]:
    payload = _city_weather(city, AIR_POLLUTION_URL)
    if not isinstance(payload, dict):
        raise WeatherError("OpenWeather вернул некорректные данные о качестве воздуха.")
    return payload


def _get_weather_description(payload: dict[str, Any]) -> str:
    try:
        return str(payload["weather"][0]["description"]).capitalize()
    except (KeyError, IndexError, TypeError) as exc:
        raise WeatherError("В ответе OpenWeather отсутствует описание погоды.") from exc


def format_current_weather(city: str, payload: dict[str, Any]) -> str:
    try:
        temperature = float(payload["main"]["temp"])
        feels_like = float(payload["main"]["feels_like"])
        humidity = int(payload["main"]["humidity"])
        wind_speed = float(payload["wind"]["speed"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("В ответе OpenWeather отсутствуют данные о погоде.") from exc

    return (
        f"🌤 Погода сегодня — {city}\n"
        f"{_get_weather_description(payload)}\n"
        f"🌡 Температура: {temperature:.1f} °C (ощущается как {feels_like:.1f} °C)\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind_speed:.1f} м/с"
    )


def format_five_day_forecast(city: str, payload: dict[str, Any]) -> str:
    try:
        forecasts = payload["list"]
        city_info = payload["city"]
        offset = int(city_info["timezone"])
        if not isinstance(forecasts, list) or not forecasts:
            raise ValueError("forecast list is missing")

        lines = [f"📅 Прогноз на 5 дней — {city} (шаг 3 часа)"]
        current_date = None
        for forecast in forecasts[:40]:
            date = datetime.fromtimestamp(
                int(forecast["dt"]) + offset, tz=timezone.utc
            )
            main = forecast["main"]
            description = forecast["weather"][0]["description"]
            if date.date() != current_date:
                current_date = date.date()
                lines.append(
                    f"\n{date:%d.%m} ({WEEKDAYS[date.weekday()]})"
                )
            lines.append(
                f"{date:%H:%M} — {float(main['temp']):.1f} °C, "
                f"{str(description).capitalize()}"
            )
        if len(lines) == 1:
            raise ValueError("forecast list is empty")
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        raise WeatherError("Не удалось прочитать прогноз на 5 дней OpenWeather.") from exc
    return "\n".join(lines)


def format_air_quality(city: str, payload: dict[str, Any]) -> str:
    try:
        result = payload["list"][0]
        aqi = int(result["main"]["aqi"])
        components = result["components"]
        if aqi not in AIR_QUALITY_LABELS:
            raise ValueError("invalid air quality index")
        pm25 = float(components["pm2_5"])
        pm10 = float(components["pm10"])
        co = float(components["co"])
        no2 = float(components["no2"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise WeatherError(
            "Не удалось прочитать данные о качестве воздуха OpenWeather."
        ) from exc

    return (
        f"🍃 Качество воздуха — {city}\n"
        f"Индекс: {aqi}/5 — {AIR_QUALITY_LABELS[aqi]}\n"
        f"PM2.5: {pm25:.1f} мкг/м³ · PM10: {pm10:.1f} мкг/м³\n"
        f"CO: {co:.1f} мкг/м³ · NO₂: {no2:.1f} мкг/м³"
    )
