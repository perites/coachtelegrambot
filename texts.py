import confg
import sessions_types
import re


class Text:
    date_format = "%d.%m"
    time_format = "%H:%M"

    @staticmethod
    def ukr_weekday(weekday_number):
        ukr_week = [
            "Понеділок",
            "Вівторок",
            "Середа",
            "Четвер",
            "П'ятниця",
            "Субота",
            "Неділя"
        ]
        return ukr_week[weekday_number]

    @staticmethod
    def ukr_group_type(group_type):
        ukr_group_type = {
            "mm": "Майстермайнд",
            "group": "Групова сесія"
        }

        return ukr_group_type[group_type]

    @staticmethod
    def unmarkdown(text):
        text = text or ""
        new_unmarked_text = re.sub(r'([*_`\[\]\(\)~>#\-=|{}!])', r'\\\1', text)

        return new_unmarked_text

    def date_representation(self, date, reverse=False):
        if reverse:
            text = f"{self.ukr_weekday(date.weekday())} {date:{Text.date_format}}"
            return text

        text = f"{date:{Text.date_format}} {self.ukr_weekday(date.weekday())}"

        return text

    def user_representation(self, user, coach=False, unmark=True):
        if not unmark:
            client_info = f"{user.full_name}"
            client_info += f" (@{user.username})"
            if not coach:
                client_info += f" контакт: {user.contact}" if user.contact else ""

            client_info += f" id:{user.id}"

            return client_info

        client_info = f"{self.unmarkdown(user.full_name)}"
        client_info += f" (@{self.unmarkdown(user.username)})"
        if not coach:
            client_info += f" контакт: {user.contact}" if user.contact else ""

        return client_info

    def session_representation_for_client(self, session, type_needed=False, link_needed=False):

        if session.type:
            session_type = sessions_types.ALL_SESSIONS_TYPES[session.type].ukr_name
        else:
            session_type = "Поки немає"

        text = (f"\n*Коуч*: {self.unmarkdown(session.coach.full_name)}\n"
                f"*Сторінка коуча*: [посилання]({session.coach.social_link})\n"
                f"*Дата*: {session.date:{self.date_format}}\n"
                f"*Час за Києвом*: {session.starting_time:{self.time_format}}\n"
                )
        if type_needed:
            text += f"*Тип*: {session_type}\n"

        if link_needed:
            if session.coach.meeting_link:
                text += f"*Посилання на зустріч*: [посилання]({session.coach.meeting_link})\n"
        return text

    def session_representation_for_coach(self, session):
        text = self.session_representation_for_client(session, type_needed=True, link_needed=True)

        client_info = self.user_representation(session.client) if session.client else "Поки немає"

        text += (
            f"*Статус*: {confg.SESSIONS_STATUSES[session.status][1]}\n"
            f"*Клієнт*: {client_info}\n")
        text += f"*Нотатка коуча*: {self.unmarkdown(session.coach_notes)}\n\n"

        return text

    def group_session_representation_for_client(self, session):

        text = f'''
*Тема групової сесії*: {self.unmarkdown(session.theme)}
*Тип події*: {self.ukr_group_type(session.type)}
*Ім'я та прізвище коуча*: {self.unmarkdown(session.coach.full_name)}
*Сторінка коуча для ознайомлення*: [посилання]({session.coach.social_link})
*Дата проведення*: {session.date:{self.date_format}}
*Час за Києвом*: {session.starting_time:{self.time_format}}
*Посилання на онлайн-кімнату, де проходитиме захід*: [посилання]({session.link_to_meeting})
'''
        return text

    def group_session_representation_for_coach(self, session):
        text = self.group_session_representation_for_client(session)
        clients = list(map(lambda n: self.user_representation(n.client), session.clients))

        amount_clients = f"{len(clients)}/{session.max_participants}"
        text += f"*Кількість кліентів*: {amount_clients}\n"

        text += f"*Клієнти*: {'  |  '.join(clients)}"

        return text

    @staticmethod
    def button_group_sessions_representation(session):
        text = f"{session.theme}"
        return text

    def notify_coach_session_booked(self, session, client=None, group=False):
        text = (f"Ваша сесія була заброньована!\n"
                f"Кліент: ")

        client_info = self.user_representation(client if client else session.client)
        text += client_info + "\n"

        if group:
            text += self.group_session_representation_for_coach(session)
        else:
            text += self.session_representation_for_coach(session)

        return text
