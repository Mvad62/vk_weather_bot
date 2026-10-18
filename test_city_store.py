import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import city_store
from keyboards import CITY_BUTTON, get_main_menu_keyboard


class CityStoreTests(unittest.TestCase):
    def test_main_menu_contains_city_selection_button(self):
        keyboard = json.loads(get_main_menu_keyboard())
        labels = [
            button["action"]["label"]
            for row in keyboard["buttons"]
            for button in row
        ]

        self.assertIn(CITY_BUTTON, labels)

    def test_city_is_saved_per_user_and_can_be_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "cities.sqlite3"
            with patch.object(city_store, "DATABASE_PATH", database_path):
                self.assertIsNone(city_store.get_city(1001))

                city_store.set_city(1001, "Казань")
                city_store.set_city(1002, "Пермь")
                self.assertEqual(city_store.get_city(1001), "Казань")
                self.assertEqual(city_store.get_city(1002), "Пермь")

                city_store.set_city(1001, "Тула")
                self.assertEqual(city_store.get_city(1001), "Тула")
                self.assertEqual(city_store.get_city(1002), "Пермь")


if __name__ == "__main__":
    unittest.main()
