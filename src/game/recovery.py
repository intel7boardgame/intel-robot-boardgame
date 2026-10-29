"""실패 복구: 재시도 후에도 안 되면 사람에게 도움을 요청합니다."""
from typing import Callable

MAX_RETRY = 2


def with_retry(action: Callable[[], object], ok: Callable[[], bool], tries: int = MAX_RETRY + 1) -> bool:
    """action을 실행하고 ok()가 참이 될 때까지 최대 tries번 시도합니다."""
    for _ in range(tries):
        action()
        if ok():
            return True
    return False
