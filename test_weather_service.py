import unittest
from unittest.mock import Mock, patch

from weather_service import (
    CURRENT_WEATHER_URL,
    FIVE_DAY_FORECAST_URL,
    GEOCODING_URL,
    REVERSE_GEOCODING_URL,
    WeatherError,
    format_air_quality,
    format_current_weather,
    format_five_day_forecast,
    get_city_by_coordinates,
    get_current_weather,
    get_five_day_forecast,
    get_weather_by_coordinates,
)


class WeatherServiceTests(unittest.TestCase):
    def test_current_weather_is_formatted_in_celsius(self):
        text = format_current_weather(
            "Казань",
            {
                "main": {"temp": 12.4, "feels_like": 10.1, "humidity": 70},
                "wind": {"speed": 3.2},
                "weather": [{"description": "небольшой дождь"}],
            },
        )

        self.assertIn("Погода сегодня — Казань", text)
        self.assertIn("12.4 °C", text)
        self.assertIn("Небольшой дождь", text)

    def test_forecast_formats_forty_three_hourly_intervals(self):
        payload = {
            "city": {"timezone": 0},
            "list": [
                {
                    "dt": 1_798_934_400 + interval * 10_800,
                    "main": {"temp": 5 + interval / 10},
                    "weather": [{"description": "ясно"}],
                }
                for interval in range(40)
            ],
        }

        text = format_five_day_forecast("Тула", payload)

        self.assertIn("Прогноз на 5 дней — Тула (шаг 3 часа)", text)
        self.assertEqual(text.count("°C"), 40)
        self.assertIn("00:00 — 5.0 °C", text)
        self.assertIn("21:00 — 5.7 °C", text)

    @patch("weather_service.API_KEY", "test-key")
    @patch("weather_service.requests.get")
    def test_forecast_uses_free_five_day_forecast_endpoint(self, get):
        geocode = Mock(status_code=200)
        geocode.json.return_value = [{"lat": 54.2, "lon": 37.6}]
        forecast = Mock(status_code=200)
        forecast.json.return_value = {"city": {}, "list": []}
        get.side_effect = (geocode, forecast)

        get_five_day_forecast("Тула")

        self.assertEqual(get.call_args_list[1].args[0], FIVE_DAY_FORECAST_URL)
        self.assertEqual(
            get.call_args_list[1].kwargs["params"],
            {
                "lat": 54.2,
                "lon": 37.6,
                "lang": "ru",
                "units": "metric",
                "appid": "test-key",
            },
        )

    def test_air_quality_includes_index_and_pollutants(self):
        text = format_air_quality(
            "Пермь",
            {
                "list": [
                    {
                        "main": {"aqi": 2},
                        "components": {
                            "pm2_5": 4.1,
                            "pm10": 8.2,
                            "co": 201.0,
                            "no2": 1.3,
                        },
                    }
                ]
            },
        )

        self.assertIn("Индекс: 2/5 — удовлетворительное", text)
        self.assertIn("PM2.5: 4.1", text)

    @patch("weather_service.API_KEY", "")
    def test_missing_api_key_is_reported(self):
        with self.assertRaisesRegex(WeatherError, "OPENWEATHER_API_KEY"):
            get_current_weather("Москва")

    @patch("weather_service.API_KEY", "test-key")
    @patch("weather_service.requests.get")
    def test_weather_by_coordinates_uses_direct_current_weather_request(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {"name": "Казань", "main": {"temp": 12}}
        get.return_value = response

        weather = get_weather_by_coordinates(55.7961, 49.1064)

        self.assertEqual(weather["name"], "Казань")
        get.assert_called_once_with(
            CURRENT_WEATHER_URL,
            params={
                "lat": 55.7961,
                "lon": 49.1064,
                "units": "metric",
                "lang": "ru",
                "appid": "test-key",
            },
            timeout=10,
        )

    @patch("weather_service.requests.get")
    def test_weather_by_coordinates_rejects_invalid_coordinates(self, get):
        with self.assertRaisesRegex(WeatherError, "Широта"):
            get_weather_by_coordinates(91, 0)
        get.assert_not_called()

    @patch("weather_service.API_KEY", "test-key")
    @patch("weather_service.requests.get")
    def test_each_city_request_is_geocoded_independently(self, get):
        responses = []
        for lat, lon in ((55.75, 37.62), (59.94, 30.31)):
            geocode = Mock(status_code=200)
            geocode.json.return_value = [{"lat": lat, "lon": lon}]
            current = Mock(status_code=200)
            current.json.return_value = {"name": "city"}
            responses.extend((geocode, current))
        get.side_effect = responses

        get_current_weather("Москва")
        get_current_weather("Санкт-Петербург")

        self.assertEqual(get.call_count, 4)
        self.assertEqual(get.call_args_list[0].args[0], GEOCODING_URL)
        self.assertEqual(get.call_args_list[0].kwargs["params"]["q"], "Москва")
        self.assertEqual(get.call_args_list[1].args[0], CURRENT_WEATHER_URL)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["lat"], 55.75)
        self.assertEqual(get.call_args_list[2].args[0], GEOCODING_URL)
        self.assertEqual(get.call_args_list[2].kwargs["params"]["q"], "Санкт-Петербург")
        self.assertEqual(get.call_args_list[3].args[0], CURRENT_WEATHER_URL)
        self.assertEqual(get.call_args_list[3].kwargs["params"]["lon"], 30.31)

    @patch("weather_service.API_KEY", "test-key")
    @patch("weather_service.requests.get")
    def test_reverse_geocoding_resolves_vk_coordinates_to_local_city(self, get):
        response = Mock(status_code=200)
        response.json.return_value = [
            {
                "name": "Kazan",
                "local_names": {"ru": "Казань"},
                "state": "Республика Татарстан",
                "country": "RU",
            }
        ]
        get.return_value = response

        city = get_city_by_coordinates(55.7961, 49.1064)

        self.assertEqual(city, "Казань, Республика Татарстан, RU")
        get.assert_called_once_with(
            REVERSE_GEOCODING_URL,
            params={
                "lat": 55.7961,
                "lon": 49.1064,
                "limit": 1,
                "appid": "test-key",
            },
            timeout=10,
        )

    @patch("weather_service.API_KEY", "test-key")
    @patch("weather_service.requests.get")
    def test_reverse_geocoding_reports_coordinates_without_city(self, get):
        with self.assertRaisesRegex(WeatherError, "Широта"):
            get_city_by_coordinates(91, 0)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
