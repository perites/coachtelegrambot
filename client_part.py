import logging
import datetime

from telebot import types

import confg
import models
import shared_variables

from database import GroupSessionToClients, get_client_by_chat_id, get_group_type_sessions, get_group_session_by_id, \
    get_group_session_with_client, get_unique_dates, get_sessions_on_date, get_session_by_id, get_session_with_client

from shared_variables import SESSIONS_TYPE_FOR_WEEK
from tools import get_session_type_by_name, CustomException

import user_states


class ClientHandler:
    bot = None

    def __init__(self):
        self.match_case_dict = dict()

    def see_my_booked_session(self, message):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Архів сесій",
                                       callback_data=f"client;client_archive;")
        )

        client = get_client_by_chat_id(message.chat.id)
        text = 'Індивідуальні сесії: \n'

        client_sessions = list(filter(lambda n: n.status == 2, client.sessions))
        client_group_sessions = list(filter(lambda n: n.status in (2, 7, 8),
                                            map(lambda n: n.group_session, client.group_sessions)))

        if not client_sessions and not client_group_sessions:
            self.bot.send_message(message.chat.id, "Ви ще не забронювали жодної сесії", reply_markup=markup)
            return

        for session in client_sessions:
            text += f'{shared_variables.tx.session_representation_for_client(session, type_needed=True)}'

        text += '\n\nСесії групового формату:\n'
        for group_session in client_group_sessions:
            text += f"{shared_variables.tx.group_session_representation_for_client(group_session)}"

        self.bot.send_message(message.chat.id, text, reply_markup=markup)

    def book_group_session(self, message):
        text, markup = self._book_group_session_parts()
        self.bot.send_message(message.chat.id, text=text, reply_markup=markup)

    @staticmethod
    def _book_group_session_parts():
        text = '''
    Мастермайнд (ММ) — це потужний інструмент для навчання та розвитку. Мета — допомогти учасникам розвивати свої навички та знання в певній галузі через обмін досвідом та з підтримкою групи ❤️


    Груповий коучинг за стандартами ICF (Міжнародна федерація коучингу) є підходом в коучингу, який зосереджується на розвитку і підтримці групи людей для досягнення їхніх особистих та професійних цілей. Ви можете приходити на зустріч із будь-яким запитом, який прямо чи опосередковано відноситься до основної теми зустрічі та знайти відповіді на своє питання, побачити нові рішення, отримати ресурс для дій 🌿

    Фокус в груповому не на думки інших, а на роботу з власним мисленням через питання, з фокусом на те, як хоче учасник, і бонусом є думки інших по їх власним запитам, що розширює усвідомлення 💡
    '''

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Записатися на майстермайдн",
                                       callback_data=f"client;group_week;;mm")
        )
        markup.add(
            types.InlineKeyboardButton("Записатися на групову сесію",
                                       callback_data=f"client;group_week;;group")
        )

        return text, markup

    def client_see_sessions_types(self, message):
        text, markup = self._client_see_sessions_types_parts()
        self.bot.send_message(message.chat.id, text, reply_markup=markup)

    @staticmethod
    def _client_see_sessions_types_parts():
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
                                               callback_data=f"client;solo_week;{session_type.type_name}")
                )
            elif not if_enough_sessions:
                markup.add(
                    types.InlineKeyboardButton(button_text,
                                               callback_data=f"client;no_sessions;{session_type.type_name}")
                )

        return text, markup

    def process_client_contact(self, message, is_contact):
        if is_contact:
            contact = message.contact.phone_number
        elif not is_contact:
            contact = message.text
        else:
            raise CustomException("Wrong value of is_contact, wrong call")

        client = models.Client.create(
            chat_id=message.chat.id,
            username=f"None-{message.chat.id}",
            full_name=message.from_user.full_name
        )

        client.contact = contact
        client.save()

        print(
            f"New client WITHOUT USERNAME was added to db: {client.username} ({client.contact}) with chat_id {client.chat_id}")
        logging.info(
            f"New client WITHOUT USERNAME was added to db: {client.username} ({client.contact}) with chat_id {client.chat_id}")

        text = f'''
Дякуємо, ваш спосіб з'вязку було збережено! 
Спосіб з'вязку : {shared_variables.tx.unmarkdown(client.contact)}
Будь ласка відправте команду /start ще раз щоб продовжити роботу з ботом
        '''
        self.bot.send_message(message.chat.id, text=text)


class ClientCallbackHandler(ClientHandler):
    def __init__(self):
        super().__init__()
        self.match_case_dict = {
            "client_archive": self.client_archive_callback_handler,

            # client book group session
            "group_week": self.group_week_callback_handler,
            "back_to_groups_types": self.back_to_groups_types_callback_handler,
            "group_session": self.group_session_callback_handler,
            "group_confirm": self.group_confirm_callback_handler,

            # client book solo session
            "no_sessions": self.no_sessions_callback_handler,
            "solo_week": self.solo_week_callback_handler,
            "back_to_sessions_type": self.back_to_sessions_type_callback_handler,
            "solo_date": self.solo_date_callback_handler,
            "solo_session": self.solo_session_callback_handler,
            "solo_confirm": self.solo_confirm_callback_handler

        }

    def client_archive_callback_handler(self, call):

        chat_id = call.chat_id
        message_id = call.message_id

        text = "Всі ваші сесії які відбулися:\n"

        client = get_client_by_chat_id(chat_id)
        client_sessions = list(filter(lambda n: n.status == 3, client.sessions))
        client_group_sessions = list(filter(lambda n: n.status == 3,
                                            map(lambda n: n.group_session, client.group_sessions)))

        if not client_sessions and not client_group_sessions:
            self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                       text="У вас ще немає жодної сесії яка відбулась")
            return

        text += 'Індивідуальні сесії:\n'
        for session in client_sessions:
            text += f'{shared_variables.tx.session_representation_for_client(session, type_needed=True)}'

        text += '\n\nСесії групового формату:\n'
        for group_session in client_group_sessions:
            text += f"{shared_variables.tx.group_session_representation_for_client(group_session)}"

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)

    def group_week_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        group_type = call.additional_info

        sessions = get_group_type_sessions(group_type)
        if not sessions:
            text = f'''
           На жаль, всі місця на групові події вже зайняті. Ви можете записатися на тему групової роботи за Донат від 200 грн на фонд проєкту ICFcoaching for WinE. Гроші фонду будуть направлені на розвиток проєкту!

           Записатися можна за посиланням: [посилання](https://forms.gle/SLyN6LpbZ1vfCA9M9)
                           '''
            self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for session in sessions:
            markup.add(
                types.InlineKeyboardButton(shared_variables.tx.button_group_sessions_representation(session),
                                           callback_data=f"client;group_session;{session.id};{group_type}")
            )
        markup.add(types.InlineKeyboardButton("Назад",
                                              callback_data=f'client;back_to_groups_types'))

        text = "Доступні події з "
        text += "Майстер майнду" if group_type == "mm" else "групового коучингу"

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                   reply_markup=markup)

    def back_to_groups_types_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id

        text, markup = self._book_group_session_parts()
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)

    def group_session_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        session = get_group_session_by_id(data)
        client = get_client_by_chat_id(chat_id)

        if get_group_session_with_client(client, group_type):
            text = f"""
           Ви вже скористалися безкоштовною можливістю з групового коучингу або мастермайнду. У вас є  можливість записатися на тему групової роботи за Донат від 200 грн на фонд проєкту ICFcoaching for WinE. Гроші фонду будуть направлені на розвиток проєкту!

           Записатися можна за посиланням: [посилання](https://forms.gle/SLyN6LpbZ1vfCA9M9)
           """
            self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                       text=text)
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(text="Так", callback_data=f'client;group_confirm;{session.id};{group_type}'))
        markup.add(types.InlineKeyboardButton(text="Ні, я змінив свою думку",
                                              callback_data=f'client;group_week;;{group_type}'))

        text = "Ви хочете прийняти участь в цій сесії?\n"
        text += f"\n*Тип події*: "
        text += "Майстермайнд\n" if group_type == "mm" else "Груповий коучинг\n"

        text += shared_variables.tx.group_session_representation_for_client(session)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text,
                                   reply_markup=markup)

    def group_confirm_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        client = get_client_by_chat_id(chat_id)
        session = get_group_session_by_id(data)
        gs_to_client = GroupSessionToClients.create(client=client,
                                                    group_session=session,
                                                    booked_at=datetime.datetime.now(confg.KYIV_TZ))

        session.status = 7
        amount_session_clients = len(session.clients)
        if amount_session_clients >= confg.MIN_AMOUNT_FOR_GROUP_SESSION:
            session.status = 8

            logging.info(f"Session with id {session.id} has more than {confg.MIN_AMOUNT_FOR_GROUP_SESSION} clients")

        if amount_session_clients == session.max_participants:
            session.status = 2

            logging.info(
                f"Session with id {session.id} has {session.max_participants} clients, now unavailable for booking")

        session.save()

        text = "Ви успішно забронювали сесію!\n\n"
        text += shared_variables.tx.group_session_representation_for_client(session)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text)

        text = shared_variables.tx.notify_coach_session_booked(session, client, group=True)
        self.bot.send_message(chat_id=session.coach.chat_id,
                              text=text)

        print(
            f"{client.username} booked {group_type} session_id {session.id} at {gs_to_client.booked_at} with {session.coach.full_name}")
        logging.info(
            f"{client.username} booked {group_type} session_id {session.id} at {gs_to_client.booked_at} with {session.coach.full_name}")

    def no_sessions_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        session_type = get_session_type_by_name(data)
        client = get_client_by_chat_id(chat_id)

        print(
            f'Client {client.username} (id:{client.id}) was TRYING to book session (type:{session_type}), but no sessions left'
        )
        logging.info(
            f'Client {client.username} (id:{client.id}) was TRYING to book session (type:{session_type}), but no sessions left')

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=session_type.no_session_text)

    def solo_week_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        shared_variables.USER_STATES[chat_id] = user_states.WantToBookSessionType(
            get_session_type_by_name(data))
        markup = types.InlineKeyboardMarkup(row_width=1)
        for date in get_unique_dates():
            markup.add(
                types.InlineKeyboardButton(shared_variables.tx.date_representation(date.date),
                                           callback_data=f"client;solo_date;{date.date}")
            )
        markup.add(types.InlineKeyboardButton("Назад",
                                              callback_data=f'client;back_to_sessions_type'))
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Доступні дати: ", reply_markup=markup)

    def back_to_sessions_type_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id

        text, markup = self._client_see_sessions_types_parts()
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)

    def solo_date_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        markup = types.InlineKeyboardMarkup(row_width=1)

        sessions = get_sessions_on_date(data)
        if not sessions:
            raise CustomException(f"No sessions on this date: {data}", chat_id)
        for session in sessions:
            markup.add(
                types.InlineKeyboardButton(f"{session.coach.full_name} "
                                           f"{session.starting_time:{shared_variables.tx.time_format}}",
                                           callback_data=f"client;solo_session;{session.id}")
            )

        user_state = shared_variables.USER_STATES.get(chat_id)
        if not user_state:
            raise CustomException(f"No state associated with this chat_id", chat_id)
        back_button = types.InlineKeyboardButton("Назад",
                                                 callback_data=f'client;solo_week;{user_state.session_type.type_name}')
        markup.add(back_button)

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=f"Виберіть сесію у {shared_variables.tx.date_representation(sessions[0].date, True)}",
                                   reply_markup=markup)

    def solo_session_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        session = get_session_by_id(data)
        client = get_client_by_chat_id(chat_id)

        user_state = shared_variables.USER_STATES.get(chat_id)
        if not user_state:
            raise CustomException(f"No state associated with this chat_id", chat_id)
        session_type = user_state.session_type
        if get_session_with_client(client, session_type):
            text = f"""
        Ви вже раніше забронювали чи відвідали безкоштовну сесію цього типу, *сесія НЕ була заброньована*.
        Ви можете отримати сесію за донат, для цього залиште заявку в формі:
        [посилання на форму]({confg.BOOK_SESSION_LINK})
        """
            self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                       text=text)
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(text="Так", callback_data=f'client;solo_confirm;{session.id}'))
        markup.add(types.InlineKeyboardButton(text="Ні, я змінив свою думку",
                                              callback_data=f'client;solo_date;{session.date}'))

        text = "Ви хочете забронювати цю сесію?\n"

        user_state = shared_variables.USER_STATES.get(chat_id)
        if not user_state:
            raise CustomException(f"No state associated with this chat_id", chat_id)
        text += f"\n*Тип коучінгу*: {user_state.session_type.ukr_name}\n"

        text += shared_variables.tx.session_representation_for_client(session)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text,
                                   reply_markup=markup)

    def solo_confirm_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        client = get_client_by_chat_id(chat_id)

        session = get_session_by_id(data)
        session.client = client
        user_state = shared_variables.USER_STATES.get(chat_id)
        if not user_state:
            raise CustomException(f"No state associated with this chat_id", chat_id)
        session.type = user_state.session_type.type_name
        session.status = 2
        session.booked_at = datetime.datetime.now(confg.KYIV_TZ)
        session.save()

        text = "Ви успішно забронювали сесію!"
        text += shared_variables.tx.session_representation_for_client(session)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text, )

        text = shared_variables.tx.notify_coach_session_booked(session)
        self.bot.send_message(chat_id=session.coach.chat_id,
                              text=text)

        print(
            f"{client.username} booked session {session.id} at {session.booked_at} with {session.coach.full_name}")
        logging.info(
            f"{client.username} booked session_id {session.id} at {session.booked_at} with {session.coach.full_name}")
