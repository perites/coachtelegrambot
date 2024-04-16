import logging
from telebot import types, apihelper

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
        except apihelper.ApiTelegramException as some_api_error:
            if some_api_error == "A request to the Telegram API was unsuccessful. Error code: 400. Description: Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message":
                notify_users_and_admins = False
            else:
                notify_users_and_admins = True

            eh = BotExceptionHandler(exception_obj=some_api_error, notify_users_and_admins=notify_users_and_admins)
            eh.handle_exception()

        except Exception as e:
            eh = BotExceptionHandler(exception_obj=e, arg=args[0], func=func)
            eh.handle_exception()

    return wrapper


class BotExceptionHandler:
    def __init__(self, exception_obj, arg=None, func=None, notify_users_and_admins=True):
        self.exception_obj = exception_obj
        self.notify_users_and_admins = notify_users_and_admins
        self.arg = arg
        self.func = func.__name__ if func else "No info"
        self.chat_id = self.get_chat_id_from_args() if arg else "No args"

    def handle_exception(self):
        if not self.notify_users_and_admins or (
                isinstance(self.exception_obj, CustomException) and self.exception_obj.ignore):
            logging.info(f"Exception : {self.exception_obj} | WAS IGNORED")
            return

        additional_text = f"User: {self.chat_id} | user_notified: {bool(self.chat_id)}"

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
Якщо проблема залишилась і ви бачите це повідомлення знов, будь ласка напишіть в підтримку {confg.SUPPORT_USERNAME}
Текст помилки:
{self.exception_obj}
Функція:
{self.func}
            '''

        shared_variables.bot.send_message(self.chat_id, text=text, parse_mode=None)


class CustomException(Exception):
    def __init__(self, message, chat_id=None, ignore=False):
        super().__init__()
        self.message = message
        self.chat_id = chat_id
        self.ignore = ignore

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
