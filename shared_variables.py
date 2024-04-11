import telebot
import confg
import texts
import sessions_types

bot = telebot.TeleBot(confg.BOT_TOKEN)

USER_STATES = dict()

tx = texts.Text()

SESSIONS_TYPE_FOR_WEEK = [
    sessions_types.Career("2024-02-01", "2024-04-21"),
    sessions_types.Leadership("2024-04-01", "2024-04-21"),
]
