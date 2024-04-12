from peewee import PostgresqlDatabase, Model, TextField, DateField, TimeField, ForeignKeyField, \
    IntegerField, DateTimeField
import confg

db = PostgresqlDatabase(confg.DATABASE_INFO["name"],
                        user=confg.DATABASE_INFO["user"],
                        password=confg.DATABASE_INFO["password"],
                        host=confg.DATABASE_INFO["host"],
                        port=confg.DATABASE_INFO["port"])


class Client(Model):
    chat_id = TextField(unique=True, null=True)
    username = TextField(unique=True)
    full_name = TextField(null=True)
    contact = TextField(null=True)

    class Meta:
        database = db


class Coach(Model):
    full_name = TextField(null=True)
    social_link = TextField(null=True)
    username = TextField()
    chat_id = TextField(null=True)

    class Meta:
        database = db


class Session(Model):
    coach = ForeignKeyField(Coach, backref="sessions")
    date = DateField()
    starting_time = TimeField()
    client = ForeignKeyField(Client, backref="sessions", null=True)
    coach_notes = TextField(null=True)
    type = TextField(null=True)
    status = IntegerField()
    booked_at = DateTimeField()

    class Meta:
        database = db


class GroupSession(Model):
    type = TextField()
    theme = TextField()
    date = DateField()
    starting_time = TimeField()
    coach = ForeignKeyField(Coach, backref="sessions")
    status = IntegerField()
    link_to_meeting = TextField()
    max_participants = IntegerField(default=6)
    coach_notes = TextField(null=True)

    class Meta:
        database = db


class GroupSessionToClients(Model):
    group_session = ForeignKeyField(GroupSession, backref='clients')
    client = ForeignKeyField(Client, backref="group_sessions")
    booked_at = DateTimeField()

    class Meta:
        database = db
