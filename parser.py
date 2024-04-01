import csv
from database import Client, Coach, Session
from datetime import datetime

# path = "C:/Users/nikit/Downloads/sessions_02_2024.csv"
path = ''
with open(path, newline='', encoding="UTF-8") as free_sessions:
    # reader = free_sessions.readlines()
    reader = csv.reader(free_sessions)
    # print(len(reader))
    for row in reader:
        row = row[0].split(';')
        print(row, "new line")
        #
        #     print(row[5])
        #     # username = row[5][1:]
        coach = Coach.get_or_create(username=row[1], defaults={'full_name': row[0], "social_link": None})
        print(coach[1])
        # print(coach)
        #     # # #         # print(coach)
        if row[5] and row[6]:
            client = Client.create(
                username=row[6],
                full_name=row[5],
            )
        else:
            client = None
        #     # # #
        session = Session.create(coach=coach[0], client=client,
                                 date=datetime.strptime(row[2] + ".24", '%d.%m.%y'),
                                 starting_time=datetime.strptime(row[4], "%H.%M"),
                                 status=3, type="Career")
# break
