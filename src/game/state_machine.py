"""한 턴의 상태 흐름. 잘못된 순서의 호출은 transitions가 예외로 막습니다."""
from transitions import Machine

STATES = ["idle", "rolling", "reading", "moving", "checking", "event", "end"]

TRANSITIONS = [
    {"trigger": "roll", "source": "idle", "dest": "rolling"},
    {"trigger": "read", "source": "rolling", "dest": "reading"},
    {"trigger": "reroll", "source": "reading", "dest": "rolling"},
    {"trigger": "move", "source": "reading", "dest": "moving"},
    {"trigger": "check", "source": "moving", "dest": "checking"},
    {"trigger": "retry", "source": "checking", "dest": "moving"},
    {"trigger": "do_event", "source": "checking", "dest": "event"},
    {"trigger": "next_turn", "source": "event", "dest": "idle"},
    {"trigger": "finish", "source": "event", "dest": "end"},
]


class TurnMachine:
    def __init__(self):
        Machine(model=self, states=STATES, transitions=TRANSITIONS, initial="idle")
