import confg
import sessions_types
import re


class Text:
    date_format = "%d.%m"
    time_format = "%H:%M"

    def ukr_weekday(self, weekday_number):
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

    def date_representation(self, date, reverse=False):
        if reverse:
            text = f"{self.ukr_weekday(date.weekday())} {date:{Text.date_format}}"
            return text

        text = f"{date:{Text.date_format}} {self.ukr_weekday(date.weekday())}"

        return text

    def session_representation_for_client(self, session, type_needed=False):

        if session.type:
            session_type = sessions_types.ALL_SESSIONS_TYPES[session.type].ukr_name
        else:
            session_type = "Поки немає"

        text = (f"\n*Коуч*: {unmarkdown(session.coach.full_name)}\n"
                f"*Сторінка коуча*: [посилання]({session.coach.social_link})\n"
                f"*Дата*: {session.date:{self.date_format}}\n"
                f"*Час*: {session.starting_time:{self.time_format}}\n"
                )
        if type_needed:
            text += f"*Тип*: {session_type}\n"
        return text

    def session_representation_for_coach(self, session):
        text = self.session_representation_for_client(session, type_needed=True)

        client_info = f"{unmarkdown(session.client.full_name)} (@{unmarkdown(session.client.username)})" if session.client else "Поки немає"

        text += (
            f"*Статус*: {confg.SESSIONS_STATUSES[session.status][1]}\n"
            f"*Клієнт*: {client_info}\n")
        text += f"*Нотатка коуча*: {unmarkdown(session.coach_notes)}\n\n"

        return text

    def group_session_representation_for_coach(self, session):
        text = self.group_session_representation_for_client(session)
        clients = list(map(lambda n: "@" + unmarkdown(n.client.username), list(session.clients)))
        amount_clients = f"{len(clients)}/{session.max_participants}"
        text += f"*Кількість кліентів*: {amount_clients}\n"

        text += f"*Клієнти*: {', '.join(clients)}"

        return text

    def notify_coach_session_booked(self, session, client=None, group=False):
        client_username = client.username if client else session.client.username
        client_full_name = client.full_name if client else session.client.full_name
        text = f"Користувач @{unmarkdown(client_username)} ({unmarkdown(client_full_name)}) забронював сесію з вами.\n"
        if group:
            text += self.group_session_representation_for_coach(session)
        elif not group:
            text += self.session_representation_for_coach(session)

        return text

    def group_session_representation_for_client(self, session):

        text = f'''
*Тема групової сесії*: {unmarkdown(session.theme)}
*Тип події*: {session.type}
*Ім'я та прізвище коуча*: {unmarkdown(session.coach.full_name)}
*Сторінка коуча для ознайомлення*: [посилання]({session.coach.social_link})
*Дата проведення*: {session.date:{self.date_format}}
*Час за Києвом*: {session.starting_time:{self.time_format}}
*Посилання на онлайн-кімнату, де проходитиме захід*: {unmarkdown(session.link_to_meeting)}
'''
        return text

    def button_group_sessions_representaton(self, session):
        text = f"{session.theme}"
        return text


def unmarkdown(text):
    text = text or ""
    new_unmarked_text = re.sub(r'([*_`\[\]\(\)~>#+\-=|{}!])', r'\\\1', text)

    return new_unmarked_text
