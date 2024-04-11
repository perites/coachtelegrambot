import time
import schedule

import shared_variables
import confg
from database import get_filling_sessions


def run_scheduler():
    schedule.every().day.at("18:00", confg.KYIV_TZ).do(check_group_session_status)
    schedule.every().day.at("20:00", confg.KYIV_TZ).do(check_group_session_status)
    while True:
        schedule.run_pending()
        time.sleep(1)


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

    text += shared_variables.tx.group_session_representation_for_client(
        session) if not coach else shared_variables.tx.group_session_representation_for_coach(session)

    shared_variables.bot.send_message(who_to_notify.chat_id, text=text)
