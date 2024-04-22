import telebot
import confg
import texts
import sessions_types

bot = telebot.TeleBot(confg.BOT_TOKEN, threaded=False)

USER_STATES = dict()

tx = texts.Text()

SESSIONS_TYPE_FOR_WEEK = [
    sessions_types.Career("2024-04-19", "2024-04-30"),
    sessions_types.Relationship("2024-04-19", "2024-04-30"),
]
