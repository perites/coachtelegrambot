from database import get_session_of_type_amount
import confg


class SessionType:
    type_name = "name"
    info_text = "info_text"
    _button_text = "button_text"
    ukr_name = "ukr_name"
    no_session_text = "no_session_text"

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    def button_text(self):
        # free_session_amount, session_of_type_amount = get_session_of_type_amount(self.type_name, self.start_date,
        # self.end_date)

        free_session_amount, session_of_type_amount = get_session_of_type_amount(self.type_name,
                                                                                 "2024-04-11",
                                                                                 "2024-04-21")

        available_sessions_of_type_amount = confg.MAX_SESSIONS_OF_ONE_TYPE - session_of_type_amount
        # print(available_sessions_of_type_amount, free_session_amount, session_of_type_amount)

        available_sessions_amount = min(free_session_amount, available_sessions_of_type_amount)

        if available_sessions_amount <= 0:
            # return False
            return f"{self._button_text}", False

        # return False
        return f"{self._button_text} | Доступно {available_sessions_amount} з {confg.MAX_SESSIONS_OF_ONE_TYPE}", True

        # print(free_session_amount, session_of_type_amount)

        # if session_of_type_amount >= confg.MAX_SESSIONS_OF_ONE_TYPE:
        #     return False

        # return f"{self._button_text} | Вільно {confg.MAX_SESSIONS_OF_ONE_TYPE - len(sessions_of_type)} з {confg.MAX_SESSIONS_OF_ONE_TYPE}"


class Career(SessionType):
    type_name = "Career"
    info_text = """
*Карʼєрний коучинг.*
Це інтерактивний процес співпраці клієнта і коуча у сфері професійної діяльності клієнта 💡

Якщо ти хочеш:
✅  прийняти рішення - в якому напрямку кар'єри рухатись

✅ зрозуміти алгоритм подальших дій при пошуку першої роботи в ІТ

✅ зрозуміти, як краще використати свій попередній досвід,

то співпраця з карʼєрним коучем допоможе тобі подивитися на свою ситуацію комплексно, побудувати план карʼєрного розвитку, навчитися підтримувати себе на шляху змін.
"""

    _button_text = "Карʼєрний коучинг"
    ukr_name = "Кар'єрний коучинг"
    no_session_text = ("Нажаль зараз всі місця на кар'єрний коучинг закінчились, "
                       "перейдіть за посиланням якщо ви хочете забронювати сесію саме цього типу\n"
                       f"[посилання]({confg.BOOK_SESSION_LINK})")

    def __init__(self, start_date, end_date):
        super().__init__(start_date, end_date)


class Leadership(SessionType):
    type_name = "Leadership"
    info_text = """
*Коучинг лідерства.*
Вітаю! Якщо ви доєдналися до нашого проєкту, то у вас вже є лідерська позиція 💪

Якщо ти хочеш:
✅ реалізувати свій потенціал

✅ досягати своїх цілей

✅ зміцнити впевненість і віру в себе,

то співпраця з коучем лідерства допоможе тобі зрозуміти свої сильні сторони, на які ти спираєшся, розібрати, що в тобі заважає тобі досягати цілей і навчитися підтримувати себе на шляху змін.
    """
    _button_text = "Коучинг лідерства"
    ukr_name = "Коучинг лідерства"
    no_session_text = ("Нажаль зараз всі місця на коучинг лідерства закінчились, "
                       "перейдіть за посиланням якщо ви хочете забронювати сесію саме цього типу\n"
                       f"[посилання]({confg.BOOK_SESSION_LINK})")

    def __init__(self, start_date, end_date):
        super().__init__(start_date, end_date)


class Relationship(SessionType):
    type_name = "Relationship"
    info_text = '''
*Коучинг стосунків* ❤️
Спрямований на допомогу клієнтам у поліпшенні якості їхніх взаємин з іншими. Це може включати розвиток навичок спілкування, вирішення конфліктів, підвищення емоційної інтелекту тощо. 

Буде корисним, якщо ти хочеш:
✅ Покращити спілкування і розуміння з партнером
✅ Розуміти свої емоції і емоції оточуючих
✅ Навчитися керувати конфліктами
'''
    _button_text = "Коучинг стосунків"
    ukr_name = "Коучинг стосунків"

    no_session_text = ("Нажаль зараз всі місця на коучинг стосунків закінчились, "
                       "перейдіть за посиланням якщо ви хочете забронювати сесію саме цього типу\n"
                       f"[посилання]({confg.BOOK_SESSION_LINK})")

    def __init__(self, start_date, end_date):
        super().__init__(start_date, end_date)


ALL_SESSIONS_TYPES = {
    Career.type_name: Career,
    Leadership.type_name: Leadership,
    Relationship.type_name: Relationship,
}
