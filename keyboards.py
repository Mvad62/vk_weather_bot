from vkbottle import Keyboard, KeyboardButtonColor, Text


TODAY_BUTTON = "🌤 Погода сегодня"
FIVE_DAY_BUTTON = "📅 Прогноз на 5 дней"
AIR_BUTTON = "🍃 Качество воздуха"
CITY_BUTTON = "🏙 Выбрать город"
CANCEL_BUTTON = "❌ Отмена"


def get_main_menu_keyboard() -> str:
    keyboard = (
        Keyboard(one_time=False, inline=False)
        .add(Text(TODAY_BUTTON), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text(FIVE_DAY_BUTTON), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text(AIR_BUTTON), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text(CITY_BUTTON), color=KeyboardButtonColor.SECONDARY)
    )
    return keyboard.get_json()


def get_cancel_keyboard() -> str:
    return (
        Keyboard(one_time=True, inline=False)
        .add(Text(CANCEL_BUTTON), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )
