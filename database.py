from datetime import datetime, timedelta

import confg
from models import Session, Client, Coach, GroupSession, GroupSessionToClients
import logging


def update_sessions_status(func):
    def wrapper(*args, **kwargs):
        expired_sessions = Session.select().where(Session.status == 1,
                                                  Session.date <= datetime.today().date(),
                                                  Session.starting_time <= datetime.now(confg.KYIV_TZ).time())
        for session in expired_sessions:
            logging.warning(
                f"Session with id: {session.id} was canceled due to expiring")

            session.status = 6
            session.save()

        result = func(*args, **kwargs)
        return result

    return wrapper


#
# def update_group_sessions_status(func):
#     def wrapper(*args, **kwargs):
#         expired_sessions = GroupSession.select().where(GroupSession.status == 1,
#                                                        GroupSession.date - timedelta(days=1) <= datetime.today().date())
#
#         for session in expired_sessions:
#             session.status = 6
#             session.save()
#
#         result = func(*args, **kwargs)
#         return result
#
#     return wrapper


# CLIENT

def get_client_by_chat_id(chat_id):
    client = Client.get_or_none(Client.chat_id == chat_id)
    return client


def get_client_by_username(client_username):
    client = Client.get_or_none(Client.username == client_username)

    return client


# COACH
def get_coach_by_username(username):
    coach = Coach.get_or_none(Coach.username == username)
    return coach


def get_coach_by_chat_id(chat_id):
    coach = Coach.get_or_none(Coach.chat_id == chat_id)

    return coach


# SOLO SESSIONS
@update_sessions_status
def get_session_by_id(session_id):
    session = Session.get_or_none(Session.id == session_id)
    return session


# SOLO SESSIONS | client

@update_sessions_status
def get_unique_dates():
    unique_dates = Session.select(Session.date).distinct().where(Session.status == 1,
                                                                 Session.date >= datetime.today()).order_by(
        Session.date)

    return unique_dates


@update_sessions_status
def get_sessions_on_date(date_str):
    sessions = Session.select().where(Session.date == datetime.strptime(date_str, '%Y-%m-%d'),
                                      Session.status == 1).order_by(Session.starting_time)

    return sessions


@update_sessions_status
def get_session_of_type_amount(type_name, start_date, end_date):
    free_session_amount = Session.select().where(Session.status == 1).count()
    session_of_type_amount = Session.select().where(Session.type == type_name, Session.status << [2, 3, 5],
                                                    Session.date >= datetime.strptime(start_date, '%Y-%m-%d'),
                                                    Session.date <= datetime.strptime(end_date, '%Y-%m-%d')).count()

    return free_session_amount, session_of_type_amount


@update_sessions_status
def get_session_with_client(client, session_type):
    session_with_client = Session.get_or_none(Session.client == client,
                                              Session.status << [2, 3, 5],
                                              Session.type == session_type.type_name)

    return session_with_client


# SOLO SESSIONS | coach
@update_sessions_status
def get_coach_sessions_dates(coach, is_archive):
    if is_archive:
        unique_dates = Session.select(Session.date).distinct().where(Session.coach == coach,
                                                                     Session.status << [3, 4, 5, 6]).order_by(
            Session.date)

        return unique_dates

    unique_dates = Session.select(Session.date).distinct().where(Session.coach == coach,
                                                                 Session.status << [1, 2]).order_by(Session.date)
    return unique_dates


@update_sessions_status
def get_coachs_sessions_on_date(date_str, coach_chat_id):
    sessions = Session.select().where(Session.date == datetime.strptime(date_str, '%Y-%m-%d'),
                                      Session.coach == Coach.get(Coach.chat_id == coach_chat_id)).order_by(
        Session.starting_time)
    return sessions


@update_sessions_status
def get_all_booked_session_with_coach(coach):
    sessions = Session.select().where(Session.coach == coach, Session.status == 2).order_by(Session.date,
                                                                                            Session.starting_time)
    return sessions


# GROUP SESSIONS
# @update_group_sessions_status
def get_filling_sessions():
    sessions = GroupSession.select().where(GroupSession.status << [1, 7],
                                           GroupSession.date <= datetime.today().date() + timedelta(days=1))

    return sessions


# @update_group_sessions_status
def get_group_type_sessions(group_type):
    sessions = GroupSession.select().where(GroupSession.status << [1, 7, 8],
                                           GroupSession.type == group_type,
                                           GroupSession.date >= datetime.today().date(),
                                           ).order_by(
        GroupSession.date,
        GroupSession.starting_time)
    return sessions


# @update_group_sessions_status
def get_group_session_by_id(session_id):
    session = GroupSession.get_by_id(session_id)

    return session


# GROUP SESSIONS | client

# @update_group_sessions_status
def get_group_session_with_client(client, group_type):
    sessions = GroupSessionToClients.select().join(GroupSession).where(GroupSessionToClients.client == client,
                                                                       GroupSessionToClients.group_session.date >= datetime.strptime(
                                                                           "2024-04-22", '%Y-%m-%d'),
                                                                       GroupSessionToClients.group_session.date <= datetime.strptime(
                                                                           "2024-04-30", '%Y-%m-%d'),
                                                                       GroupSessionToClients.group_session.status <<
                                                                       [2, 3, 5, 7, 8],
                                                                       )

    return sessions


# GROUP SESSIONS | coach
# @update_group_sessions_status
def get_coach_group_sessions(coach, is_archive):
    if is_archive:
        sessions = GroupSession.select().where(GroupSession.coach == coach,
                                               GroupSession.status << [3, 4, 5, 6]).order_by(GroupSession.date)
        return sessions

    sessions = GroupSession.select().where(GroupSession.coach == coach,
                                           GroupSession.status << [1, 2, 7, 8]).order_by(GroupSession.date)

    return sessions
