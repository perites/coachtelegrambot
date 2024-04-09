import confg
from datetime import datetime, timedelta
from models import Session, Client, Coach, GroupSession, GroupSessionToClients, fn


def get_filling_sessions():
    sessions = GroupSession.select().where(GroupSession.status == 7,
                                           GroupSession.date <= datetime.today().date() + timedelta(days=1)
                                           )

    return sessions


def update_sessions_status(func):
    def wrapper(*args, **kwargs):
        # sessions_updated = Session.update(status=6).where(Session.status == 1,
        #                                                   Session.date <= datetime.today().date(),
        #                                                   Session.starting_time <= datetime.today().time())
        expired_sessions = Session.select().where(Session.status == 1,
                                                  Session.date <= datetime.today().date(),
                                                  Session.starting_time <= datetime.now(confg.KYIV_TZ).time())
        for session in expired_sessions:
            session.status = 6
            session.save()

        result = func(*args, **kwargs)
        return result

    return wrapper


def update_group_sessions_status(func):
    def wrapper(*args, **kwargs):
        expired_sessions = GroupSession.select().where(GroupSession.status == 1,
                                                       GroupSession.date <= datetime.today().date() - timedelta(days=1))

        for session in expired_sessions:
            session.status = 6
            session.save()

        result = func(*args, **kwargs)
        return result

    return wrapper


@update_sessions_status
def get_unique_dates():
    unique_dates = Session.select(Session.date).distinct().where(Session.status == 1,
                                                                 Session.date >= datetime.today()).order_by(
        Session.date)

    return unique_dates


@update_sessions_status
def get_coach_sessions_dates(coach):
    unique_dates = Session.select(Session.date).distinct().where(Session.coach == coach,
                                                                 Session.date >= datetime.strptime("2024-04-01",
                                                                                                   '%Y-%m-%d')).order_by(
        Session.date)
    return unique_dates


def get_client_by_username(client_username):
    client = Client.get_or_none(Client.username == client_username)

    return client


# @update_sessions_status
# def get_all_free_sessions():
#     sessions = Session.select(Session.id).where(Session.status == 1)
#
#     return len(sessions)


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


def get_session_by_id(id):
    session = Session.get_or_none(Session.id == id)
    return session


def get_coach_by_username(username):
    coach = Coach.get_or_none(Coach.username == username)
    return coach


def get_client_by_chat_id(chat_id):
    client = Client.get_or_none(Client.chat_id == chat_id)
    return client


def get_coach_by_chat_id(chat_id):
    coach = Coach.get_or_none(Coach.chat_id == chat_id)

    return coach


@update_sessions_status
def get_session_with_client(client, session_type):
    session_with_client = Session.get_or_none(Session.client == client,
                                              Session.status << [2, 3, 5],
                                              Session.type == session_type.type_name,
                                              Session.date >= datetime.strptime(session_type.start_date, '%Y-%m-%d'),
                                              Session.date <= datetime.strptime(session_type.end_date, '%Y-%m-%d')
                                              )
    return session_with_client


def get_coach_group_sessions(coach):
    sessions = GroupSession.select().where(GroupSession.coach == coach).order_by(GroupSession.date)

    return sessions


def get_session_by_week(week_number):
    sessions = Session.select().where(fn.DATE_PART('week', Session.date) == week_number).order_by(Session.date,
                                                                                                  Session.starting_time)

    return sessions


@update_group_sessions_status
def get_group_type_sessions(type):
    sessions = GroupSession.select().where(GroupSession.status << [1, 7, 8],
                                           GroupSession.type == type).order_by(GroupSession.date,
                                                                               GroupSession.starting_time)

    return sessions


@update_group_sessions_status
def get_group_session_by_id(session_id):
    session = GroupSession.get_by_id(session_id)

    return session


@update_group_sessions_status
def get_group_session_with_client(client, type):
    sessions = GroupSessionToClients.select().join(GroupSession).where(GroupSessionToClients.client == client,
                                                                       GroupSessionToClients.group_session.type == type,
                                                                       GroupSessionToClients.group_session.status << [2,
                                                                                                                      3,
                                                                                                                      5,
                                                                                                                      7,
                                                                                                                      8])

    return sessions

    # query = f"""
    #     SELECT *
    #     FROM session
    #     WHERE EXTRACT(WEEK FROM date) = {week_number}
    #     ORDER BY date
    # """
    # sessions = Session.raw(query)
    # for session in sessions:
    #     print(session.date)

# d#b.drop_tables([Session, Client, Coach])
# db.create_tables([Session, Client, Coach])
# get_session_by_week(13)
## db.drop_tables([Session, Client, Coach])
##
#
# def startover():
#     db.drop_tables([Session, Client, Coach])
#     db.create_tables([Session, Client, Coach])
#     ksenia = Coach.create(
#         name="Ksenia Petrunina",
#         social_link="inst.com/ksenia",
#     )
#     natasha = Coach.create(
#         name="Natasha Blablablabovna",
#         social_link="inst.com/natasha",
#     )
#     Session.create(
#         coach=ksenia,
#         date=datetime.strptime("14/03/24", '%d/%m/%y'),
#         starting_time=datetime.strptime("10:00:00", "%H:%M:%S")
#     )
#     Session.create(
#         coach=ksenia,
#         date=datetime.strptime("14/03/24", '%d/%m/%y'),
#         starting_time=datetime.strptime("12:30:00", "%H:%M:%S")
#     )
#     Session.create(
#         coach=natasha,
#         date=datetime.strptime("15/03/24", '%d/%m/%y'),
#         starting_time=datetime.strptime("12:00:00", "%H:%M:%S")
#     )
#     Session.create(
#         coach=natasha,
#         date=datetime.strptime("15/03/24", '%d/%m/%y'),
#         starting_time=datetime.strptime("14:30:00", "%H:%M:%S")
#     )

#
