import datetime
import time
import threading
import logging

import telebot
from telebot import types
import schedule

import confg
import user_states
import sessions_types
from models import Client, GroupSessionToClients
from texts import Text

from database import get_unique_dates, get_sessions_on_date, get_session_by_id, get_client_by_chat_id, \
    get_coach_by_username, get_coach_sessions_dates, get_coachs_sessions_on_date, get_coach_by_chat_id, \
    get_all_booked_session_with_coach, get_session_with_client, get_client_by_username, get_group_type_sessions, \
    get_group_session_by_id, get_group_session_with_client, get_filling_sessions, get_coach_group_sessions

bot = telebot.TeleBot(confg.BOT_TOKEN)

logging.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    filename=confg.LOG_PATH, filemode='w', level=logging.INFO, encoding='utf-8')

error_logger = logging.getLogger('error_logger')
error_handler = logging.FileHandler(confg.ERROR_LOG_PATH)
error_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(message)s')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)
error_logger.propagate = False

SESSIONS_TYPE_FOR_WEEK = [
    sessions_types.Career("2024-03-25", "2024-04-10"),
    sessions_types.Leadership("2024-03-25", "2024-04-10")
]


def get_session_type_by_name(type_name):
    for session_type in SESSIONS_TYPE_FOR_WEEK:
        if session_type.type_name == type_name:
            return session_type


tx = Text()

USER_STATES = dict()


def error_catcher(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            print(e)
            error_logger.exception(e)
            error_logger.error("bot didn`t stop, continuing")
            notify_admins(confg.ADMINS_CHAT_IDS, e, "bot didnt stop", func)

    return wrapper


def notify_admins(admins_chat_ids_list, error_message, additional_info, func=None):
    text = f''' 
Увага ! Відбулась помилка, продивіться ерорні логи ! 
посилання на папку з логами: [logs]({confg.LOG_FOLDER_LINK})
Інфо : 
    function : {func.__name__ if func else "No info"} 
    error: {error_message}
    info: {additional_info}
'''

    for chat_id in admins_chat_ids_list:
        bot.send_message(chat_id, text=text, parse_mode=None)


def check_group_session_status():
    sessions = get_filling_sessions()
    for session in sessions:
        notify_session_canceled(session.coach, session, coach=True)

        for client in session.clients:
            client = client.client
            notify_session_canceled(client, session)

        session.status = 4
        session.save()


def notify_session_canceled(who_to_notify, session, coach=False):
    text = (f"На жаль сесія була відмінена через недостатнью кількість учасників\n"
            f"Детальніша інформація про сесію")

    text += tx.group_session_representation_for_client(
        session) if not coach else tx.group_session_representation_for_coach(session)

    bot.send_message(who_to_notify.chat_id, text=text)


# @bot.message_handler(commands=['book_session_manually'])
# @error_catcher
# def book_session_manually(message):
#     args = message.text.split("---")[1:]
#     if not args:
#         bot.send_message(message.chat.id, "Wrong format, no arguments were given")
#         return
#
#     session_id = args[0].split(':')[1] if "session_id" in args[0] else None
#     try:
#         session_id = int(session_id)
#     except Exception as e:
#         bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
#         return
#
#     if not session_id:
#         bot.send_message(message.chat.id, "Wrong format, session_id wasnt found")
#         return
#
#     session = get_session_by_id(session_id)
#     if not session:
#         bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
#         return
#     # print(session.coach.full_name, session.date)
#
#     full_name = args[1].split(':')[1] if "full_name" in args[1] else None
#     username = args[2].split(':')[1] if "username" in args[2] else None
#     if not full_name or not username:
#         bot.send_message(message.chat.id, "Wrong format, full_name or username wasnt found")
#         return
#     client = Client.create(full_name=full_name, username=username)
#     old_client = session.client
#     session.client = client
#     session.save()
#
#     logging.info(
#         f"{client.username} booked session {session.date} at {session.starting_time} with {session.coach.full_name}")
#
#     bot.send_message(message.chat.id,
#                      f"success!\nSession id: {session.id}\nDate: {session.date}\nTime: {session.starting_time}\nOld client: {old_client}\nNew client id: {session.client.id}\nNew client username: @{session.client.username}\nNew client full_name: {session.client.full_name}")
#
#     if not session.coach.chat_id:
#         logging.info(f"not chat id for {session.coach}. Message was not send to coach")
#         return
#     text = tx.notify_coach_session_booked(session)
#     bot.send_message(chat_id=session.coach.chat_id,
#                      text=text)


@bot.message_handler(commands=['start'])
@error_catcher
def start(message: types.Message):
    client = get_client_by_username(message.from_user.username) or get_client_by_chat_id(message.chat.id)
    if not client:
        client = Client.create(
            chat_id=message.chat.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        print(f"New client was added to db: {client.username} with chat_if {client.chat_id}")
        logging.info(f"New client was added to db: {client.username} with chat_if {client.chat_id}")
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
        bot.send_message(message.chat.id, text, reply_markup=markup)

        if sessions := get_all_booked_session_with_coach(coach):

            for session in sessions:
                text = tx.notify_coach_session_booked(session)
                bot.send_message(chat_id=session.coach.chat_id,
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

    bot.send_message(message.chat.id, text, reply_markup=markup)


# Coach part
@bot.message_handler(func=lambda message: message.text == "Подивитись мої сесії")
@error_catcher
def see_my_session(message):
    if not (coach := get_coach_by_username(message.from_user.username)):
        print(f"{message.from_user.username} was NOT authorized as coach")
        logging.warning(f"{message.from_user.username} was NOT authorized as coach")

        text = ("Ви не зареестровані в базі як коуч, в доступі відмовлено\n"
                "Напишіть /start щоб почати заново")
        bot.send_message(message.chat.id, text)

        return

    text, markup = see_my_session_in()

    bot.send_message(message.chat.id, text=text, reply_markup=markup)


def see_my_session_in():
    text = "Виберіть тип сесій: "
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Індивідуальний формат", callback_data="coach_session;single"),
        types.InlineKeyboardButton("Груповий формат", callback_data='coach_session;group')
    )
    return text, markup


@bot.callback_query_handler(func=lambda call: call.data.split(";")[0] == "coach_session")
@error_catcher
def handle_coach_session_callback_query(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    callback_data = call.data.split(";")
    level = callback_data[1]
    data = callback_data[2] if len(callback_data) > 2 else None
    type = callback_data[3] if len(callback_data) > 3 else None

    match level:
        case "single":
            coach = get_coach_by_chat_id(chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            for date in get_coach_sessions_dates(coach):
                markup.add(
                    types.InlineKeyboardButton(tx.date_representation(date.date),
                                               callback_data=f"coach_session;date;{date.date}")
                )

            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Ваші одиночні сесії:",
                                  reply_markup=markup)

        case "group":
            coach = get_coach_by_chat_id(chat_id)
            markup = types.InlineKeyboardMarkup(row_width=1)
            for session in get_coach_group_sessions(coach):
                markup.add(
                    types.InlineKeyboardButton(tx.button_group_sessions_representaton(session),
                                               callback_data=f"coach_session;session;{session.id};group")
                )
            markup.add(types.InlineKeyboardButton("Назад", callback_data=f'coach_session;back_to_types'))
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Ваші групові сесії:",
                                  reply_markup=markup)

        case "back_to_types":

            text, markup = see_my_session_in()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

        case "date":
            markup = types.InlineKeyboardMarkup(row_width=1)
            sessions = get_coachs_sessions_on_date(data, coach_chat_id=chat_id)
            for session in sessions:
                markup.add(
                    types.InlineKeyboardButton(
                        f"{session.starting_time:{tx.time_format}} {confg.SESSIONS_STATUSES[session.status][1]}",
                        callback_data=f"coach_session;session;{session.id};single")
                )
            back_button = types.InlineKeyboardButton("Назад", callback_data='coach_session;single')
            markup.add(back_button)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Всі ваші сесії за {session.date:{tx.date_format}}",
                                  reply_markup=markup)

        case "session":
            if type == "single":
                session = get_session_by_id(data)
                text = tx.session_representation_for_coach(session)
            elif type == "group":
                session = get_group_session_by_id(data)
                text = tx.group_session_representation_for_coach(session)

            markup = types.InlineKeyboardMarkup(row_width=2)

            starting_datetime = datetime.datetime.combine(session.date, session.starting_time)
            starting_datetime = starting_datetime.replace(tzinfo=confg.KYIV_TZ)

            if (session.status == 2 or session.status == 8 and

                    starting_datetime + datetime.timedelta(hours=1) <= datetime.datetime.now(confg.KYIV_TZ)):
                yes_button = types.InlineKeyboardButton("Так",
                                                        callback_data=f'coach_session;session_happened_yes;{session.id};{type}')
                no_button = types.InlineKeyboardButton("Ні",
                                                       callback_data=f'coach_session;session_happened_no;{session.id};{type}')
                markup.add(yes_button, no_button)
                text += "\n\nЧи сесія відбулась ?"

            callback_data = f'coach_session;date;{session.date}' if type == "single" else "coach_session;group"
            markup.add(types.InlineKeyboardButton("Назад", callback_data=callback_data))
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

        case "session_happened_yes":
            session = get_session_by_id(data) if type == "single" else get_group_session_by_id(data)
            session.status = 3
            session.save()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Чудово ! Дякуємо за відповідь")

        case "session_happened_no":
            session = get_session_by_id(data) if type == "single" else get_group_session_by_id(
                data)
            markup = types.InlineKeyboardMarkup(row_width=2)
            canceled_button = types.InlineKeyboardButton("Відмінена",
                                                         callback_data=f'coach_session;session_canceled;{session.id};{type}')
            postponed_button = types.InlineKeyboardButton("Перенесена",
                                                          callback_data=f'coach_session;session_postponed;{session.id};{type}')
            markup.add(canceled_button, postponed_button)
            if type == "single":
                text = f"{tx.session_representation_for_coach(session)}"
            elif type == "group":
                text = f'{tx.group_session_representation_for_coach(session)}'

            text += "Сесія не була і не буде проведена (Відмінена) чи Перенесена ?"
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

            #

        case "session_canceled":
            session = get_session_by_id(data) if type == "single" else get_group_session_by_id(
                data)
            session.status = 4
            session.save()

            if type == "single":
                text = f"{tx.session_representation_for_coach(session)}"
            elif type == "group":
                text = f'{tx.group_session_representation_for_coach(session)}'

            text += "\n\nБудь ласка опишіть в повідомленні чому сесія не відбулась"

            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text)

            USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id, type)

        case "session_postponed":
            session = get_session_by_id(data) if type == "single" else get_group_session_by_id(
                data)
            session.status = 5
            session.save()

            if type == "single":
                text = f"{tx.session_representation_for_coach(session)}"
            elif type == "group":
                text = f'{tx.group_session_representation_for_coach(session)}'

            text += "\n\nБудь ласка опишіть в повідомленні чому сесія була пересена"

            USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id, type)

            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text)


@bot.message_handler(
    func=lambda message: isinstance(USER_STATES.get(message.chat.id), user_states.WaitingForCoachSessionNote))
@error_catcher
def process_session_notes(message: types.Message):
    chat_id = message.chat.id
    user_state = USER_STATES.get(chat_id)

    session = get_session_by_id(
        user_state.session_id) if user_state.session_type == "single" else get_group_session_by_id(
        user_state.session_id)
    session.coach_notes = message.text
    session.save()

    del USER_STATES[chat_id]

    bot.reply_to(message, "Дякуємо за відповідь, відповідь збережена")


# Client part
@bot.message_handler(func=lambda message: message.text == "Мої заброньовані сесії")
@error_catcher
def see_my_booked_session(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Архів сесій",
                                   callback_data=f"client_archive;")
    )

    client = get_client_by_chat_id(message.chat.id)
    text = 'Індивідуальні сесії: \n'

    client_sessions = filter(lambda n: n.status == 2, client.sessions)
    client_group_sessions = filter(lambda n: n.status in (2, 7, 8),
                                   map(lambda n: n.group_session, client.group_sessions))

    if not client_sessions or not client_group_sessions:
        bot.send_message(message.chat.id, "Ви ще не забронювали жодної сесії")
        return

    for session in client_sessions:
        text += f'{tx.session_representation_for_client(session, type_needed=True)}'

    text += '\n\nСесії групового формату:\n'
    for group_session in client_group_sessions:
        text += f"{tx.group_session_representation_for_client(group_session)}"

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.split(";")[0] == "client_archive")
@error_catcher
def handle_client_archive_callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    text = "Всі ваші сесії які відбулися:\n"

    client = get_client_by_chat_id(chat_id)
    client_sessions = list(filter(lambda n: n.status == 3, client.sessions))
    client_group_sessions = list(filter(lambda n: n.status == 3,
                                        map(lambda n: n.group_session, client.group_sessions)))

    if not client_sessions or not client_group_sessions:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="У вас ще немає жодної сесії яка відбулась")
        return

    text += 'Індивідуальні сесії:\n'
    for session in client_sessions:
        text += f'{tx.session_representation_for_client(session, type_needed=True)}'

    text += '\n\nСесії групового формату:\n'
    for group_session in client_group_sessions:
        text += f"{tx.group_session_representation_for_client(group_session)}"

    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: message.text == "Групові формати")
@error_catcher
def book_group_session(message):
    text, markup = book_group_sessions_in()
    bot.send_message(message.chat.id, text=text, reply_markup=markup)


def book_group_sessions_in():
    text = '''
        мм - це ;
        груповий коучинг - це 
        '''

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Записатися на майстер майдн",
                                   callback_data=f"book_group;week;;mm")
    )
    markup.add(
        types.InlineKeyboardButton("Записатися на групову сесію",
                                   callback_data=f"book_group;week;;group")
    )

    return text, markup


@bot.callback_query_handler(func=lambda call: call.data.split(";")[0] == "book_group")
@error_catcher
def handle_book_mm_callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    callback_data = call.data.split(";")
    level = callback_data[1]
    data = callback_data[2] if len(callback_data) > 2 else None
    group_type = callback_data[3] if len(callback_data) > 3 else None
    match level:
        case "week":
            sessions = get_group_type_sessions(group_type)
            if not sessions:
                text = f'''
Нажаль зараз всі місця на групові події закінчились, перейдіть за посиланням ПРИДУМАТИ ДАЛІ"
[посилання]({confg.BOOK_SESSION_LINK})
                '''
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
                return
            markup = types.InlineKeyboardMarkup(row_width=1)
            for session in sessions:
                markup.add(
                    types.InlineKeyboardButton(tx.button_group_sessions_representaton(session),
                                               callback_data=f"book_group;session;{session.id};{group_type}")
                )
            markup.add(types.InlineKeyboardButton("Назад",
                                                  callback_data=f'book_group;back_to_groups_types'))

            text = "Доступні сесії з"
            text += "майстер майнду" if group_type == "mm" else "групових сеанісів"
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                  reply_markup=markup)

        case "back_to_groups_types":
            text, markup = book_group_sessions_in()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)

        case "session":
            session = get_group_session_by_id(data)

            client = get_client_by_chat_id(chat_id)
            if existing_session := get_group_session_with_client(client, group_type):
                text = f"""
Згідно з правилами проєкту, ви маєте право відвідати тільки одну подію в кожному з групових форматів під час кожної хвилі.

Свої заброньовані сесії можна побачити в розділі *Мої заброньовані сесії*
"""
                bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                      text=text)
                return

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton(text="Так", callback_data=f'book_group;confirm;{session.id};{group_type}'))
            markup.add(types.InlineKeyboardButton(text="Ні, я змінив свою думку",
                                                  callback_data=f'book_group;week;;{group_type}'))

            text = "Ви хочете прийняти участь в цій сесії?\n"
            text += f"\n*Груповий тип*:"
            text += "майстер майнд\n" if group_type == "mm" else "груповий сеанc\n"

            text += tx.group_session_representation_for_client(session)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

        case "confirm":
            client = get_client_by_chat_id(chat_id)

            session = get_group_session_by_id(data)

            gs_to_client = GroupSessionToClients.create(client=client,
                                                        group_session=session,
                                                        booked_at=datetime.datetime.now(confg.KYIV_TZ))

            session.status = 7
            amount_session_clients = len(session.clients)
            if amount_session_clients >= confg.MIN_AMOUNT_FOR_GROUP_SESSION:
                session.status = 8

            if amount_session_clients == session.max_participants:
                session.status = 2

            session.save()

            text = "Ви успішно забронювали сесію!"
            text += tx.group_session_representation_for_client(session)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text)

            text = tx.notify_coach_session_booked(session, client, group=True)
            bot.send_message(chat_id=session.coach.chat_id,
                             text=text)

            print(
                f"{client.username} booked {group_type} session_id {session.id} at {gs_to_client.booked_at} with {session.coach.full_name}")
            logging.info(
                f"{client.username} booked {group_type} session_id {session.id} at {gs_to_client.booked_at} with {session.coach.full_name}")

    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: message.text == "Індивідуальні сесії")
@error_catcher
def client_see_sessions_types(message):
    text, markup = client_see_sessions_types_in()
    bot.send_message(message.chat.id, text, reply_markup=markup)


def client_see_sessions_types_in():
    text = """
Зараз доступні такі спеціалізації коучингу:

"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    for session_type in SESSIONS_TYPE_FOR_WEEK:
        text += f'{session_type.info_text}\n'
        button_text, if_enough_sessions = session_type.button_text()
        if if_enough_sessions:
            markup.add(
                types.InlineKeyboardButton(button_text,
                                           callback_data=f"book_menu;week;{session_type.type_name}")
            )
        elif not if_enough_sessions:
            markup.add(
                types.InlineKeyboardButton(button_text,
                                           callback_data=f"book_menu;no_sessions;{session_type.type_name}")
            )

    return text, markup


@bot.callback_query_handler(func=lambda call: call.data.split(";")[0] == "book_menu")
@error_catcher
def handle_book_menu_callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    callback_data = call.data.split(";")
    level = callback_data[1]
    data = callback_data[2] if len(callback_data) > 2 else None
    match level:
        case "no_sessions":
            session_type = get_session_type_by_name(data)

            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=session_type.no_session_text)

        case "week":
            USER_STATES[chat_id] = user_states.WantToBookSessionType(
                get_session_type_by_name(data))
            markup = types.InlineKeyboardMarkup(row_width=1)
            for date in get_unique_dates():
                markup.add(
                    types.InlineKeyboardButton(tx.date_representation(date.date),
                                               callback_data=f"book_menu;date;{date.date}")
                )
            markup.add(types.InlineKeyboardButton("Назад",
                                                  callback_data=f'book_menu;back_to_sessions_type'))
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Доступні дати: ", reply_markup=markup)

        case 'back_to_sessions_type':
            text, markup = client_see_sessions_types_in()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)

        case "date":
            markup = types.InlineKeyboardMarkup(row_width=1)
            sessions = get_sessions_on_date(data)
            for session in sessions:
                markup.add(
                    types.InlineKeyboardButton(f"{session.coach.full_name} "
                                               f"{session.starting_time:{tx.time_format}}",
                                               callback_data=f"book_menu;session;{session.id}")
                )
            back_button = types.InlineKeyboardButton("Назад",
                                                     callback_data=f'book_menu;week;{USER_STATES[chat_id].session_type.type_name}')
            markup.add(back_button)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Виберіть сесію у {tx.date_representation(session.date, True)}",
                                  reply_markup=markup)

        case "session":
            session = get_session_by_id(data)

            client = get_client_by_chat_id(chat_id)
            session_type = USER_STATES[chat_id].session_type
            if existing_session := get_session_with_client(client, session_type):
                text = f"""
Ви вже раніше забронювали чи відвідали безкоштовну сесію цього типу, *сесія НЕ була заброньована*.
Ви можете отримати сесію за донат, для цього залиште заявку в формі:
[посилання на форму]({confg.BOOK_SESSION_LINK})
"""
                bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                      text=text)
                return

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton(text="Так", callback_data=f'book_menu;confirm;{session.id}'))
            markup.add(types.InlineKeyboardButton(text="Ні, я змінив свою думку",
                                                  callback_data=f'book_menu;date;{session.date}'))

            text = "Ви хочете забронювати цю сесію?\n"
            text += f"\n*Тип коучінгу*: {USER_STATES[chat_id].session_type.ukr_name}\n"

            text += tx.session_representation_for_client(session)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

        case "confirm":
            client = get_client_by_chat_id(chat_id)

            session = get_session_by_id(data)
            session.client = client
            session.type = USER_STATES[chat_id].session_type.type_name
            session.status = 2
            session.booked_at = datetime.datetime.now(confg.KYIV_TZ)
            session.save()

            text = "Ви успішно забронювали сесію!"
            text += tx.session_representation_for_client(session)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text, )

            text = tx.notify_coach_session_booked(session)
            bot.send_message(chat_id=session.coach.chat_id,
                             text=text)

            print(
                f"{client.username} booked session {session.id} at {session.booked_at} with {session.coach.full_name}")
            logging.info(
                f"{client.username} booked session_id {session.id} at {session.booked_at} with {session.coach.full_name}")

    bot.answer_callback_query(call.id)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    try:
        print(f"now:{datetime.datetime.now()} kyiv tz: {datetime.datetime.now(confg.KYIV_TZ)} --- starting bot")
        schedule.every().day.at("18:00", confg.KYIV_TZ).do(check_group_session_status)
        schedule.every().day.at("20:00", confg.KYIV_TZ).do(check_group_session_status)

        start_bot = threading.Thread(target=bot.polling)
        start_bot.start()

        run_scheduler_thread = threading.Thread(target=run_scheduler)
        run_scheduler_thread.start()


    except Exception as e:
        print(e)
        error_logger.exception(e)
        error_logger.error("BOT STOPPED")
        notify_admins(confg.ADMINS_CHAT_IDS, e, "bot STOPPED")
