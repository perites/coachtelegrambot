class State:
    def __init__(self, name):
        self.state_name = name


class WaitingForClientContact(State):
    def __init__(self):
        super().__init__("WaitingForClientContact")


class WaitingForCoachSessionNote(State):
    def __init__(self, session_id, session_type):
        super().__init__("WaitingForSessionNoteState")
        self.session_id = session_id
        self.session_type = session_type


class WantToBookSessionType(State):
    def __init__(self, session_type):
        super().__init__("WantToBookSessionType")
        self.session_type = session_type
