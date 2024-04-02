import datetime
import logging
import user_states
import telebot
from telebot import types
import sessions_types
import confg
from database import get_unique_dates, get_sessions_on_date, get_session_by_id, get_client_by_chat_id, \
    get_coach_by_username, get_coach_sessions_dates, get_coachs_sessions_on_date, get_coach_by_chat_id, \
    get_all_booked_session_with_coach, get_session_with_client, get_client_by_username

from models import Client
from texts import Text

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

tx = Text()

USER_STATES = dict()

SESSIONS_TYPE_FOR_WEEK = [
    sessions_types.Career("2024-03-25", "2024-04-10"),
    sessions_types.Leadership("2024-03-25", "2024-04-10")
]


def get_session_type_by_name(type_name):
    for session_type in SESSIONS_TYPE_FOR_WEEK:
        if session_type.type_name == type_name:
            return session_type


def error_catcher(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            print(e)
            error_logger.exception(e)
            notify_admins(confg.ADMINS_CHAT_IDS, args, kwargs, func)

    return wrapper


def notify_admins(admins_chat_ids_list, args, kwargs, func=None):
    text = f''' 
    Увага ! Відбулась помилка, продивіться ерорні логи ! 
    посилання на папку з логами: [logs]({confg.LOG_FOLDER_LINK})
    Інфо : 
        function : {func.__name__ if func else "No info"} 
        args : {args}
        kwargs: {kwargs}    
            '''

    for chat_id in admins_chat_ids_list:
        bot.send_message(chat_id, text=text)


@bot.message_handler(commands=['book_session_manually'])
@error_catcher
def book_session_manually(message):
    args = message.text.split("---")[1:]
    if not args:
        bot.send_message(message.chat.id, "Wrong format, no arguments were given")
        return

    session_id = args[0].split(':')[1] if "session_id" in args[0] else None
    try:
        session_id = int(session_id)
    except Exception as e:
        bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
        return

    if not session_id:
        bot.send_message(message.chat.id, "Wrong format, session_id wasnt found")
        return

    session = get_session_by_id(session_id)
    if not session:
        bot.send_message(message.chat.id, "Wrong session_id, wasnt found")
        return
    # print(session.coach.full_name, session.date)

    full_name = args[1].split(':')[1] if "full_name" in args[1] else None
    username = args[2].split(':')[1] if "username" in args[2] else None
    if not full_name or not username:
        bot.send_message(message.chat.id, "Wrong format, full_name or username wasnt found")
        return
    client = Client.create(full_name=full_name, username=username)
    old_client = session.client
    session.client = client
    session.save()

    logging.info(
        f"{client.username} booked session {session.date} at {session.starting_time} with {session.coach.full_name}")

    bot.send_message(message.chat.id,
                     f"success!\nSession id: {session.id}\nDate: {session.date}\nTime: {session.starting_time}\nOld client: {old_client}\nNew client id: {session.client.id}\nNew client username: @{session.client.username}\nNew client full_name: {session.client.full_name}")

    if not session.coach.chat_id:
        logging.info(f"not chat id for {session.coach}. Message was not send to coach")
        return
    text = tx.notify_coach_session_booked(session)
    bot.send_message(chat_id=session.coach.chat_id,
                     text=text)


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
    markup.add(types.KeyboardButton("Записатися на індивідуальну сесію"))
    markup.add(types.KeyboardButton("Записатися на групову сесію"))
    markup.add(types.KeyboardButton("Мої заброньовані сесії"))

    print(f"{message.from_user.username} was authorized as user")
    logging.info(f"{message.from_user.username} was authorized as user")

    text = """
Вітаємо тебе в просторі WinE!

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

    markup = types.InlineKeyboardMarkup(row_width=1)
    for date in get_coach_sessions_dates(coach):
        markup.add(
            types.InlineKeyboardButton(tx.date_representation(date.date),
                                       callback_data=f"coach_session;date;{date.date}")
        )
    bot.send_message(message.chat.id, "Ваші сесії: ", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.split(";")[0] == "coach_session")
@error_catcher
def handle_coach_session_callback_query(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    callback_data = call.data.split(";")
    level = callback_data[1]
    data = callback_data[2] if len(callback_data) > 2 else None

    match level:
        case "date":
            markup = types.InlineKeyboardMarkup(row_width=1)
            sessions = get_coachs_sessions_on_date(data, coach_chat_id=chat_id)
            for session in sessions:
                markup.add(
                    types.InlineKeyboardButton(
                        f"{session.starting_time:{tx.time_format}} {confg.SESSIONS_STATUSES[session.status][1]}",
                        callback_data=f"coach_session;session;{session.id}")
                )
            back_button = types.InlineKeyboardButton("Назад", callback_data='coach_session;back_to_available_dates')
            markup.add(back_button)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Всі ваші сесії за {session.date:{tx.date_format}}",
                                  reply_markup=markup)

        case "session":
            session = get_session_by_id(data)

            text = tx.session_representation_for_coach(session)

            markup = types.InlineKeyboardMarkup(row_width=2)

            starting_datetime = datetime.datetime.combine(session.date, session.starting_time)
            starting_datetime = starting_datetime.replace(tzinfo=confg.KYIV_TZ)

            if (session.status == 2 and

                    starting_datetime + datetime.timedelta(hours=1) <= datetime.datetime.now(confg.KYIV_TZ)):
                yes_button = types.InlineKeyboardButton("Так",
                                                        callback_data=f'coach_session;session_happened_yes;{session.id}')
                no_button = types.InlineKeyboardButton("Ні",
                                                       callback_data=f'coach_session;session_happened_no;{session.id}')
                markup.add(yes_button, no_button)
                text += "\n\nЧи сесія відбулась ?"

            markup.add(types.InlineKeyboardButton("Назад", callback_data=f'coach_session;date;{session.date}'))
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=text,
                                  reply_markup=markup)

        case "session_happened_yes":
            session = get_session_by_id(data)
            session.status = 3
            session.save()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"Чудово ! Дякуємо за відповідь",
                                  # Опишіть чому сесія з {session.client.full_name} за {session.date:{tx.date_format}} о {session.starting_time:{tx.time_format}} відбулась
                                  )
            # USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id)

        case "session_happened_no":
            session = get_session_by_id(data)
            markup = types.InlineKeyboardMarkup(row_width=2)
            canceled_button = types.InlineKeyboardButton("Відмінена",
                                                         callback_data=f'coach_session;session_canceled;{session.id}')
            postponed_button = types.InlineKeyboardButton("Перенесена",
                                                          callback_data=f'coach_session;session_postponed;{session.id}')
            markup.add(canceled_button, postponed_button)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"{tx.session_representation_for_coach(session)}Сесія не була і не буде проведена (Відмінена) чи Перенесена ?",
                                  reply_markup=markup)

            #

        case "session_canceled":
            session = get_session_by_id(data)
            session.status = 4
            session.save()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"{tx.session_representation_for_coach(session)}\n\nБудь ласка опишіть в повідомленні чому сесія не відбулась",
                                  )
            USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id)

        case "session_postponed":
            session = get_session_by_id(data)
            session.status = 5
            session.save()

            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=f"{tx.session_representation_for_coach(session)}\n\nБудь ласка опишіть в повідомленні чому сесія була пересена",
                                  )
            USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id)

        case "back_to_available_dates":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for date in get_coach_sessions_dates(get_coach_by_chat_id(chat_id)):
                markup.add(
                    types.InlineKeyboardButton(tx.date_representation(date.date),
                                               callback_data=f"coach_session;date;{date.date}")
                )
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Ваші сесії: ",
                                  reply_markup=markup)


@bot.message_handler(
    func=lambda message: isinstance(USER_STATES.get(message.chat.id), user_states.WaitingForCoachSessionNote))
@error_catcher
def process_session_notes(message: types.Message):
    chat_id = message.chat.id
    user_state = USER_STATES.get(chat_id)

    session = get_session_by_id(user_state.session_id)
    session.coach_notes = message.text
    session.save()

    del USER_STATES[chat_id]

    bot.reply_to(message, "Дякуємо за відповідь, відповідь збережена")


# Client part
@bot.message_handler(func=lambda message: message.text == "Мої заброньовані сесії")
@error_catcher
def see_my_booked_session(message: types.Message):
    client = get_client_by_chat_id(message.chat.id)
    text = ''
    client_sessions = client.sessions
    if not client_sessions:
        bot.send_message(message.chat.id, "Ви ще не забронювали жодної сесії")
        return

    for session in client_sessions:
        text += f'\n{tx.session_representation_for_client(session, type_needed=True)}\n'
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == "Записатися на групову сесію")
@error_catcher
def book_group_session(message):
    bot.send_message(message.chat.id, "Станом на зараз записатись на групові сесії можливий тільки через сайт, "
                                      "будь ласка перейдіть за посиланням і запишіться там\n"
                                      f"[посилання]({confg.GROUP_SESSION_LINK})")


@bot.message_handler(func=lambda message: message.text == "Записатися на індивідуальну сесію")
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

        # if not button_text:
        #     markup.add(
        #         types.InlineKeyboardButton(f"{session_type._button_text}",
        #                                    callback_data=f"book_menu;no_sessions;{session_type.type_name}")
        #     )
        # else:
        #     markup.add(
        #         types.InlineKeyboardButton(button_text,
        #                                    callback_data=f"book_menu;week;{session_type.type_name}")
        #     )

    return text, markup


# @bot.message_handler(func=lambda message: message.text == "Доступні дати")
# def see_available_dates(message):
#     markup = types.InlineKeyboardMarkup(row_width=1)
#     for date in get_unique_dates():
#         markup.add(
#             types.InlineKeyboardButton(tx.date_representation(date.date),
#                                        callback_data=f"book_menu;date;{date.date}")
#         )
#
#     bot.send_message(message.chat.id, "Доступні дати: ", reply_markup=markup)


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
            # add_row_to_table(session.coach.full_name, session.coach.social_link, session.date, session.starting_time,
            #                  UKR_WEEK[session.date.strftime('%A')],
            #                  session.client.full_name, session.client.username)
            print(
                f"{client.username} booked session {session.id} at {session.booked_at} with {session.coach.full_name}")
            logging.info(
                f"{client.username} booked session_id {session.id} at {session.booked_at} with {session.coach.full_name}")

    bot.answer_callback_query(call.id)
    # case "back_to_available_dates":
    #     markup = types.InlineKeyboardMarkup(row_width=1)
    #     for date in get_unique_dates():
    #         markup.add(
    #             types.InlineKeyboardButton(tx.date_representation(date.date),
    #                                        callback_data=f"book_menu;date;{date.date}")
    #         )
    #
    #     bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Доступні дати: ", reply_markup=markup)


if __name__ == '__main__':
    try:
        print("Starting bot...")
        bot.polling()
    except Exception as e:
        print(e)
        error_logger.exception(e)
