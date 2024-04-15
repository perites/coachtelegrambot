import telebot
import confg
import texts
import sessions_types

bot = telebot.TeleBot(confg.BOT_TOKEN)

USER_STATES = dict()

tx = texts.Text()

SESSIONS_TYPE_FOR_WEEK = [
    sessions_types.Career("2024-04-11", "2024-04-21"),
    sessions_types.Relationship("2024-04-15", "2024-04-21"),
]
