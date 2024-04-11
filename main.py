import datetime
import logging
import threading

from telebot import types

import confg
import shared_variables

from tools import error_catcher, CallbackHandler, ExceptionHandler
from database import get_client_by_chat_id, get_coach_by_username, get_all_booked_session_with_coach, \
    get_client_by_username

from client_part import ClientHandler, ClientCallbackHandler
from coach_part import CoachHandler, CoachCallbackHandler

from models import Client
import my_scheduler
import user_states

ClientHandler.bot = shared_variables.bot
client_handler = ClientHandler()

CoachHandler.bot = shared_variables.bot
coach_handler = CoachHandler()

CallbackHandler.callers = {
    "client": ClientCallbackHandler(),
    "coach": CoachCallbackHandler()
}


# @shared_variables.bot.message_handler(commands=['book_session_manually'])
# @error_catcher
# def book_session_manually(message):
#     args = message.text.split("---")[1:]
#     if not args:
#         shared_variables.bot.send_message(message.chat.id, "Wrong format, no arguments were given")
#         return
#
#     session_id = args[0].split(':')[1] if "session_id" in args[0] else None
#     try:
#         session_id = int(session_id)
#     except Exception as e:
#         shared_variables.bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
#         return
#
#     if not session_id:
#         shared_variables.bot.send_message(message.chat.id, "Wrong format, session_id wasnt found")
#         return
#
#     session = get_session_by_id(session_id)
#     if not session:
#         shared_variables.bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
#         return
#     # print(session.coach.full_name, session.date)
#
#     full_name = args[1].split(':')[1] if "full_name" in args[1] else None
#     username = args[2].split(':')[1] if "username" in args[2] else None
#     if not full_name or not username:
#         shared_variables.bot.send_message(message.chat.id, "Wrong format, full_name or username wasnt found")
#         return
#     client = Client.create(full_name=full_name, username=username)
#     old_client = session.client
#     session.client = client
#     session.save()
#
#     logging.info(
#         f"{client.username} booked session {session.date} at {session.starting_time} with {session.coach.full_name}")
#
#     shared_variables.bot.send_message(message.chat.id,
#                      f"success!\nSession id: {session.id}\nDate: {session.date}\nTime: {session.starting_time}\nOld client: {old_client}\nNew client id: {session.client.id}\nNew client username: @{session.client.username}\nNew client full_name: {session.client.full_name}")
#
#     if not session.coach.chat_id:
#         logging.info(f"not chat id for {session.coach}. Message was not send to coach")
#         return
#     text = shared_variables.tx.notify_coach_session_booked(session)
#     shared_variables.bot.send_message(chat_id=session.coach.chat_id,
#                      text=text)


@shared_variables.bot.message_handler(commands=['start'])
@error_catcher
def start(message: types.Message):
    if shared_variables.USER_STATES.get(message.chat.id):
        del shared_variables.USER_STATES[message.chat.id]

    client = get_client_by_chat_id(message.chat.id) or get_client_by_username(message.from_user.username)
    if not client:

        if message.from_user.username:
            username = message.from_user.username
        elif not message.from_user.username:
            username = f"None-{message.chat.id}"
        else:
            raise Exception

        client = Client.create(
            chat_id=message.chat.id,
            username=username,
            full_name=message.from_user.full_name
        )

        print(f"New client was added to db: {client.username} with chat_id {client.chat_id}")
        logging.info(f"New client was added to db: {client.username} with chat_id {client.chat_id}")
    else:
        client.chat_id = message.chat.id
        client.save()
        print(f"Client {client.username} was updatated with chat_id: {client.chat_id}")
        logging.info(f"Client {client.username} was updatated with chat_id: {client.chat_id}")

    if coach := get_coach_by_username(message.from_user.username):
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton("Подивитись мої сесії"))

        print(f"{message.from_user.username} was authorized as coach")
        logging.info(f"{message.from_user.username} was authorized as coach")

        coach.chat_id = message.chat.id
        coach.save()

        text = (f"Вітаємо, {coach.full_name}.\n"
                f"Ви авторизувались як коуч")
        shared_variables.bot.send_message(message.chat.id, text, reply_markup=markup)

        if sessions := get_all_booked_session_with_coach(coach):

            for session in sessions:
                text = shared_variables.tx.notify_coach_session_booked(session)
                shared_variables.bot.send_message(chat_id=session.coach.chat_id,
                                                  text=text)

        return

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("Індивідуальні сесії"))
    markup.add(types.KeyboardButton("Групові формати"))
    markup.add(types.KeyboardButton("Мої заброньовані сесії"))

    print(f"{message.from_user.username} was authorized as user")
    logging.info(f"{message.from_user.username} was authorized as user")

    text = """
Вітаємо тебе в просторі проєкту ICFcoaching for WinE!

Це простір коучингової підтримки і особистого розвитку.

Тут ти можеш записатися на індивідуальні коуч сесії, а також на групові формати роботи до професіоналів ICF!
"""

    shared_variables.bot.send_message(message.chat.id, text, reply_markup=markup)


@shared_variables.bot.callback_query_handler(func=lambda call: call)
@error_catcher
def handle_callback_query(call):
    call_handler = CallbackHandler(call)
    call_handler.handle_caller()


# Coach part
@shared_variables.bot.message_handler(func=lambda message: message.text == "Подивитись мої сесії")
@error_catcher
def see_my_session(message):
    coach_handler.see_my_session(message)


@shared_variables.bot.message_handler(
    func=lambda message: isinstance(shared_variables.USER_STATES.get(message.chat.id),
                                    user_states.WaitingForCoachSessionNote))
@error_catcher
def process_session_notes(message: types.Message):
    coach_handler.process_session_notes(message)


# Client part
@shared_variables.bot.message_handler(func=lambda message: message.text == "Мої заброньовані сесії")
@error_catcher
def see_my_booked_session(message: types.Message):
    client_handler.see_my_booked_session(message)


@shared_variables.bot.message_handler(func=lambda message: message.text == "Групові формат")
@error_catcher
def book_group_session_temp(message):
    text = f"Станом на зараз записатись на групові сесії можливий тільки через сайт, будь ласка перейдіть за посиланням і запишіться там\n[посилання]({confg.GROUP_SESSION_LINK})"

    shared_variables.bot.send_message(message.chat.id, text=text)


@shared_variables.bot.message_handler(func=lambda message: message.text == "Групові формати")
@error_catcher
def book_group_session(message):
    client_handler.book_group_session(message)


@shared_variables.bot.message_handler(func=lambda message: message.text == "Індивідуальні сесії")
@error_catcher
def client_see_sessions_types(message):
    client_handler.client_see_sessions_types(message)


if __name__ == '__main__':
    try:
        print(f"now:{datetime.datetime.now()} kyiv tz: {datetime.datetime.now(confg.KYIV_TZ)} --- starting bot")

        start_bot = threading.Thread(target=shared_variables.bot.polling)
        start_bot.start()

        run_scheduler_thread = threading.Thread(target=my_scheduler.run_scheduler)
        run_scheduler_thread.start()

    except Exception as e:
        eh = ExceptionHandler(exception_obj=e, bot_stopped=True)
        eh.handle_exception()
