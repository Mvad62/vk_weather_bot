import os
from pathlib import Path

from dotenv import load_dotenv
from vkbottle import API, BuiltinStateDispenser
from vkbottle.bot import BotLabeler

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

VK_TOKEN = (os.getenv("VK_TOKEN") or "").strip()
api = API(token=VK_TOKEN)
labeler = BotLabeler()
state_dispenser = BuiltinStateDispenser()
