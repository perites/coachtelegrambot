import logging
import datetime

from telebot import types

import confg
import shared_variables

from database import get_coach_by_username, get_session_by_id, get_group_session_by_id, get_coach_by_chat_id, \
    get_coach_sessions_dates, get_coach_group_sessions, get_coachs_sessions_on_date
from tools import CustomException

import user_states


class CoachHandler:
    bot = None

    def __init__(self):
        self.match_case_dict = dict()

    def see_my_session(self, message: types.Message):
        self._check_if_user_is_coach(message.from_user.username, message.chat.id)
        text, markup = self._see_my_session_parts()

        self.bot.send_message(message.chat.id, text=text, reply_markup=markup)

    @staticmethod
    def _see_my_session_parts(archive=False):

        callback_data_solo = "coach;show;single"
        callback_data_group = 'coach;show;group'
        if archive:
            callback_data_solo += ";archive"
            callback_data_group += ";archive"

        text = "Виберіть тип сесій: "
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Індивідуальний формат", callback_data=callback_data_solo),
            types.InlineKeyboardButton("Груповий формат", callback_data=callback_data_group)
        )
        return text, markup

    @staticmethod
    def _get_session(session_id, group_type):
        match group_type:
            case "single":
                session = get_session_by_id(session_id)
                message_text = f"{shared_variables.tx.session_representation_for_coach(session)}"
            case "group":
                session = get_group_session_by_id(session_id)
                message_text = f"{shared_variables.tx.group_session_representation_for_coach(session)}"
            case _:
                raise CustomException(f"Invalid group type: {group_type}")

        return session, message_text

    def process_session_notes(self, message):
        chat_id = message.chat.id
        user_state = shared_variables.USER_STATES.get(chat_id)

        session, _ = self._get_session(user_state.session_id, user_state.session_type)
        session.coach_notes = message.text
        session.save()

        del shared_variables.USER_STATES[chat_id]

        self.bot.reply_to(message, "Дякуємо за відповідь, відповідь збережена")

    def coach_archive(self, message):
        self._check_if_user_is_coach(message.from_user.username, message.chat.id)
        text, markup = self._see_my_session_parts(archive=True)

        self.bot.send_message(message.chat.id, text=text, reply_markup=markup)

    def _check_if_user_is_coach(self, username, chat_id):
        if not get_coach_by_username(username):
            print(f"{username} was NOT authorized as coach")
            logging.warning(f"{username} was NOT authorized as coach")

            text = ("Ви не зареестровані в базі як коуч, в доступі відмовлено\n"
                    "Напишіть /start щоб почати заново")

            self.bot.send_message(chat_id=chat_id, text=text)

            raise CustomException(f"{username} was NOT authorized as coach", ignore=True)

        return True


class CoachCallbackHandler(CoachHandler):
    def __init__(self):
        super().__init__()
        self.match_case_dict = {
            "show": self.show_callback_handler,
            "back_to_types": self.back_to_types_callback_handler,
            "date": self.date_callback_handler,
            "session": self.session_callback_handler,

            "session_happened_yes": self.session_happened_yes_callback_handler,
            "session_happened_no": self.session_happened_no_callback_handler,
            "session_canceled": self.session_canceled_callback_handler,
            "session_postponed": self.session_postponed_callback_handler

        }

    def show_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        is_archive = call.additional_info or ""

        coach = get_coach_by_chat_id(chat_id)
        markup = types.InlineKeyboardMarkup(row_width=1)

        match data:
            case "single":
                for date in get_coach_sessions_dates(coach, is_archive):
                    markup.add(
                        types.InlineKeyboardButton(text=shared_variables.tx.date_representation(date.date),
                                                   callback_data=f"coach;date;{date.date}"))

                message_text = "Ваші індивідуальні сесії:"

            case "group":
                for session in get_coach_group_sessions(coach, is_archive):
                    markup.add(
                        types.InlineKeyboardButton(shared_variables.tx.button_group_sessions_representation(session),
                                                   callback_data=f"coach;session;{session.id};group"))

                message_text = "Ваші групові сесії:"

            case _:
                raise CustomException(f"Invalid group type: {data}", chat_id)

        markup.add(types.InlineKeyboardButton("Назад", callback_data=f'coach;back_to_types;;{is_archive}'))
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=message_text,
                                   reply_markup=markup)

    def back_to_types_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        is_archive = call.additional_info

        text, markup = self._see_my_session_parts(is_archive)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text,
                                   reply_markup=markup)

    def date_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data

        markup = types.InlineKeyboardMarkup(row_width=1)
        sessions = get_coachs_sessions_on_date(data, coach_chat_id=chat_id)
        if not sessions:
            raise CustomException(f"No sessions on spesified date: date:{data} coach_chat_id {chat_id}", chat_id)
        for session in sessions:
            markup.add(
                types.InlineKeyboardButton(
                    f"{session.starting_time:{shared_variables.tx.time_format}} {confg.SESSIONS_STATUSES[session.status][1]}",
                    callback_data=f"coach;session;{session.id};single")
            )
        back_button = types.InlineKeyboardButton("Назад", callback_data=f'coach;show;single')
        markup.add(back_button)
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=f"Всі ваші сесії за {sessions[0].date:{shared_variables.tx.date_format}}",
                                   reply_markup=markup)

    def session_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        match group_type:
            case "single":
                session = get_session_by_id(data)
                text = shared_variables.tx.session_representation_for_coach(session)

                callback_data = f"coach;date;{session.date}"
            case "group":
                session = get_group_session_by_id(data)
                text = shared_variables.tx.group_session_representation_for_coach(session)

                callback_data = "coach;show;group"

            case _:
                raise CustomException(f"Invalid group type: {group_type}", chat_id)

        markup = types.InlineKeyboardMarkup(row_width=2)

        starting_datetime = datetime.datetime.combine(session.date, session.starting_time)
        starting_datetime = starting_datetime.replace(tzinfo=confg.KYIV_TZ)

        if ((session.status == 2 or session.status == 8) and
                starting_datetime + datetime.timedelta(hours=1) <= datetime.datetime.now(confg.KYIV_TZ)):
            yes_button = types.InlineKeyboardButton("Так",
                                                    callback_data=f'coach;session_happened_yes;{session.id};{group_type}')
            no_button = types.InlineKeyboardButton("Ні",
                                                   callback_data=f'coach;session_happened_no;{session.id};{group_type}')
            markup.add(yes_button, no_button)
            text += "\n\nЧи сесія відбулась ?"

        markup.add(types.InlineKeyboardButton("Назад", callback_data=callback_data))
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=text,
                                   reply_markup=markup)

    def session_happened_yes_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        session, _ = self._get_session(data, group_type)

        session.status = 3
        session.save()
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=f"Чудово ! Дякуємо за відповідь")

    def session_happened_no_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        session, message_text = self._get_session(data, group_type)

        markup = types.InlineKeyboardMarkup(row_width=2)
        canceled_button = types.InlineKeyboardButton("Відмінена",
                                                     callback_data=f'coach;session_canceled;{session.id};{group_type}')
        postponed_button = types.InlineKeyboardButton("Перенесена",
                                                      callback_data=f'coach;session_postponed;{session.id};{group_type}')
        markup.add(canceled_button, postponed_button)

        message_text += "Сесія не була і не буде проведена (Відмінена) чи Перенесена ?"
        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=message_text,
                                   reply_markup=markup)

    def session_canceled_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        session, message_text = self._get_session(data, group_type)
        session.status = 4
        session.save()

        message_text += "\n\nБудь ласка опишіть в повідомленні чому сесія не відбулась"

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=message_text)

        shared_variables.USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id, group_type)

    def session_postponed_callback_handler(self, call):
        chat_id = call.chat_id
        message_id = call.message_id
        data = call.data
        group_type = call.additional_info

        session, message_text = self._get_session(data, group_type)
        session.status = 5
        session.save()

        message_text += "\n\nБудь ласка опишіть в повідомленні чому сесія була пересена"

        self.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                   text=message_text)

        shared_variables.USER_STATES[chat_id] = user_states.WaitingForCoachSessionNote(session.id, group_type)
