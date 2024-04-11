import logging
from telebot import types

import confg
import shared_variables

logging.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    filename=confg.LOG_PATH, filemode='w', level=logging.INFO, encoding='utf-8')

error_logger = logging.getLogger('error_logger')
error_handler = logging.FileHandler(confg.ERROR_LOG_PATH)
error_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(message)s')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)
error_logger.propagate = False


def error_catcher(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result

        except Exception as e:
            eh = ExceptionHandler(exception_obj=e, bot_stopped=False, arg=args[0], func=func)
            eh.handle_exception()

    return wrapper


class ExceptionHandler:
    def __init__(self, exception_obj, bot_stopped, arg=None, func=None):
        self.exception_obj = exception_obj
        self.arg = arg
        self.bot_stopped = bot_stopped
        self.func = func.__name__ if func else "No info"
        self.chat_id = self.get_chat_id_from_args()

    def handle_exception(self):
        print(self.exception_obj)

        additional_text = f"Client:{self.chat_id} | client_notified: {bool(self.chat_id)} | bot stop: {self.bot_stopped}"

        error_logger.exception(self.exception_obj)
        error_logger.error(additional_text)

        self.notify_admins(additional_text)
        if self.chat_id:
            self.notify_client()

    def get_chat_id_from_args(self):
        if isinstance(self.arg, types.Message):
            chat_id = self.arg.chat.id
            return chat_id
        if isinstance(self.arg, types.CallbackQuery):
            chat_id = self.arg.message.chat.id

            return chat_id

        return None

    def notify_admins(self, additional_text):
        text = f''' 
Увага ! Відбулась помилка, продивіться ерорні логи ! 
посилання на папку з логами: [logs]({confg.LOG_FOLDER_LINK})
Інфо: 
    function : {self.func} 
    error: {self.exception_obj}
    info: {additional_text}
'''

        for chat_id in confg.ADMINS_CHAT_IDS:
            shared_variables.bot.send_message(chat_id, text=text, parse_mode=None)

    def notify_client(self):
        text = f'''
Упс, відбулась помилка ( 

Будь ласка спробуйте вести команду /start в бота і спробувати зробити що ви хотіли ще раз, не натискайте на старі повідомлення в чаті
Якщо проблема залишилась і ви бачите це повідомлення знов, будь ласка напишіть в підтримку @kryskaks 
Текст помилки:\n{self.exception_obj}
            '''

        shared_variables.bot.send_message(self.chat_id, text=text, parse_mode=None)


class CustomException(Exception):
    def __init__(self, message, chat_id=None):
        super().__init__()
        self.message = message
        self.chat_id = chat_id

    def __str__(self):
        return self.message


class CallbackHandler:
    callers = None

    def __init__(self, call):
        self.chat_id = call.message.chat.id
        self.message_id = call.message.message_id
        self.call_id = call.id
        self.caller, self.level, self.data, self.additional_info = self._unpack_callback_data(call.data)

    @staticmethod
    def _unpack_callback_data(callback_data):
        callback_data = callback_data.split(";")
        caller = callback_data[0]
        level = callback_data[1]
        data = callback_data[2] if len(callback_data) > 2 else None
        additional_info = callback_data[3] if len(callback_data) > 3 else None
        return caller, level, data, additional_info

    def handle_caller(self):
        handler = self.callers.get(self.caller)
        if not handler:
            raise CustomException(f"No handler was found for argument {self.caller}")

        function_to_run = handler.match_case_dict.get(self.level)
        if not function_to_run:
            raise CustomException(
                f"No function was found to call argument for argument {self.level} at handler {handler}")
        function_to_run(self)
        handler.bot.answer_callback_query(self.call_id)


def get_session_type_by_name(type_name):
    for session_type in shared_variables.SESSIONS_TYPE_FOR_WEEK:
        if session_type.type_name == type_name:
            return session_type
