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


@shared_variables.bot.message_handler(commands=['start'])
@error_catcher
def start(message: types.Message):
    if shared_variables.USER_STATES.get(message.chat.id):
        del shared_variables.USER_STATES[message.chat.id]

        print(f"States were cleaned for {message.chat.id}")
        logging.info(f"States were cleaned for {message.chat.id}")

    client = get_client_by_chat_id(message.chat.id) or get_client_by_username(message.from_user.username)

    if not client:
        if not message.from_user.username:
            text = '''
У вас немає або скритий нік телеграму і в разі бронювання коуч не зможе зв'ятись з вами

Будь ласка натисніть кнопку " Поділитися номером телефону " або відправте в повідомленні зручний для вас спосіб зв'язку
(будь який спосіб який вам зручний: номер телефону, електронна пошта, посилання на інстаграм і тд.) 
'''
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button = types.KeyboardButton("Поділитися номером телефону", request_contact=True)
            markup.add(button)

            shared_variables.USER_STATES[message.chat.id] = user_states.WaitingForClientContact()

            shared_variables.bot.send_message(message.chat.id,
                                              text=text,
                                              reply_markup=markup)

            return

        client = Client.create(
            chat_id=message.chat.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )

        print(f"New client was added to db: {client.username} with chat_id {client.chat_id}")
        logging.info(f"New client was added to db: {client.username} with chat_id {client.chat_id}")
    else:
        client.chat_id = message.chat.id
        client.save()
        print(f"Client {client.username} ({client.contact}) was updatated with chat_id: {client.chat_id}")
        logging.info(f"Client {client.username} ({client.contact}) was updatated with chat_id: {client.chat_id}")

    if coach := get_coach_by_username(message.from_user.username):
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton("Подивитись мої активні сесії"))
        markup.add(types.KeyboardButton("Архів сесій"))

        print(f"{message.from_user.username} ({client.contact}) was authorized as coach")
        logging.info(f"{message.from_user.username} ({client.contact}) was authorized as coach")

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


@shared_variables.bot.message_handler(content_types=['contact'])
@error_catcher
def process_client_contact(message: types.Message):
    client_handler.process_client_contact(message, is_contact=True)


@shared_variables.bot.message_handler(func=lambda message: isinstance(shared_variables.USER_STATES.get(message.chat.id),
                                                                      user_states.WaitingForClientContact))
@error_catcher
def process_client_contact(message: types.Message):
    client_handler.process_client_contact(message, is_contact=False)


@shared_variables.bot.callback_query_handler(func=lambda call: call)
@error_catcher
def handle_callback_query(call):
    call_handler = CallbackHandler(call)
    call_handler.handle_caller()


# Coach part
@shared_variables.bot.message_handler(func=lambda message: message.text == "Подивитись мої активні сесії")
@error_catcher
def see_my_session(message):
    coach_handler.see_my_session(message)


@shared_variables.bot.message_handler(func=lambda message: message.text == "Архів сесій")
@error_catcher
def coach_archive(message):
    coach_handler.coach_archive(message)


@shared_variables.bot.message_handler(func=lambda message: isinstance(shared_variables.USER_STATES.get(message.chat.id),
                                                                      user_states.WaitingForCoachSessionNote))
@error_catcher
def process_session_notes(message: types.Message):
    coach_handler.process_session_notes(message)


# Client part
@shared_variables.bot.message_handler(func=lambda message: message.text == "Мої заброньовані сесії")
@error_catcher
def see_my_booked_session(message: types.Message):
    client_handler.see_my_booked_session(message)


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
