import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers.weather import process_geolocation


class WeatherHandlerTests(unittest.TestCase):
    def test_vk_geolocation_is_reverse_geocoded_and_saved_for_sender(self):
        message = SimpleNamespace(
            geo=SimpleNamespace(
                coordinates=SimpleNamespace(latitude=55.7961, longitude=49.1064)
            ),
            from_id=1001,
            peer_id=1001,
            answer=AsyncMock(),
        )
        delete_state = AsyncMock()

        with (
            patch(
                "handlers.weather.get_weather_by_coordinates",
                return_value={
                    "name": "Казань",
                    "main": {
                        "temp": 10.0,
                        "feels_like": 9.0,
                        "humidity": 60,
                    },
                    "wind": {"speed": 2.0},
                    "weather": [{"description": "ясно"}],
                },
            ) as get_weather,
            patch(
                "handlers.weather.get_city_by_coordinates",
                return_value="Казань, Республика Татарстан, RU",
            ) as reverse_geocode,
            patch("handlers.weather.set_city") as save_city,
            patch("handlers.weather.state_dispenser.delete", delete_state),
        ):
            asyncio.run(process_geolocation(message))

        get_weather.assert_called_once_with(55.7961, 49.1064)
        reverse_geocode.assert_called_once_with(55.7961, 49.1064)
        save_city.assert_called_once_with(1001, "Казань, Республика Татарстан, RU")
        delete_state.assert_awaited_once_with(1001)
        message.answer.assert_awaited_once()
        self.assertIn("Казань", message.answer.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
