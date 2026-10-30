"""LLM 없이 쓰는 중계 문장. Ollama가 느리거나 실패해도 게임이 멈추지 않게 합니다.

윷놀이 이벤트(docs/interfaces.md 1절: throw, move, capture, stack, finish, win, decision, help)와
주사위 게임 이벤트(2절, 차선책: from/to가 숫자인 move, win)를 모두 처리합니다.
"""
import random

from common.interfaces import Event

PLAYER = {"human": "사람", "robot": "로봇"}

EVENT_TEXT = {
    "forward": "{value}칸 앞으로",
    "back": "{value}칸 뒤로",
    "skip": "한 턴 쉬기",
    "quiz": "퀴즈",
}

CELL_TEXT = {
    "cell_0": "참먹이", "cell_5": "모 자리", "cell_10": "뒷모 자리", "cell_15": "찌모 자리", "center": "방",
    "wait": "대기 칸", "wait_human": "대기 칸", "wait_robot": "대기 칸", "goal": "완주",
}

REASON_TEXT = {
    "capture": "상대 말을 잡을 수 있어서",
    "stack": "내 말과 업을 수 있어서",
    "advance": "완주에 가장 가까운 말이라서",
    "enter": "새 말을 판에 올리려고",
}

YUT_KINDS = {"throw", "capture", "stack", "finish", "decision"}


def player_name(player: str) -> str:
    return PLAYER.get(player, player)


def josa(word: str, pair: str) -> str:
    """받침에 맞는 조사를 붙입니다. pair는 "이가", "은는", "을를", "으로"."""
    last = word.rstrip("' ")[-1:] or "가"
    code = ord(last) - 0xAC00
    final = code % 28 if 0 <= code < 11172 else 0
    if pair == "으로":
        return word + ("로" if final in (0, 8) else "으로")  # ㄹ 받침은 '로'
    return word + (pair[0] if final else pair[1])


def cell_name(cell) -> str:
    """'cell_6' → '6번 칸', 'diag_r1' → '지름길', 숫자(주사위 게임) → 'N번 칸'."""
    if isinstance(cell, int):
        return f"{cell}번 칸"
    if cell in CELL_TEXT:
        return CELL_TEXT[cell]
    if str(cell).startswith("diag_"):
        return "지름길"
    if str(cell).startswith("cell_"):
        return f"{cell[5:]}번 칸"
    return str(cell)


def event_text(info: dict) -> str:
    """이벤트 칸 정보({"type": "back", "value": 3})를 '3칸 뒤로' 같은 말로 바꿉니다."""
    if not info:
        return ""
    return EVENT_TEXT.get(info.get("type", ""), info.get("type", "")).format(value=info.get("value", ""))


def is_yut(event: Event) -> bool:
    d = event.detail
    return event.kind in YUT_KINDS or "yut" in d or "turns" in d or isinstance(d.get("from"), str)


def facts(event: Event) -> str:
    """LLM 프롬프트에 넣을 턴 사실 요약. 숫자는 이벤트 값 그대로 씁니다."""
    d = event.detail
    who = player_name(event.player)
    if event.kind == "help":
        return f"{event.turn}턴 {who} 차례. 진행 중 문제가 생겨 사람의 도움을 요청함: {d.get('message', '')}"
    if is_yut(event):
        return _yut_facts(event, who, d)
    lines = [f"{event.turn}턴, {who} 차례.", f"주사위 {d.get('dice')}."]
    info = d.get("event") or {}
    if info:
        landed = d.get("from", 0) + d.get("dice", 0)
        lines.append(f"{d.get('from')}번 칸에서 {landed}번 칸에 도착, 이벤트 칸 효과 '{event_text(info)}'.")
        lines.append(f"최종 위치 {d.get('to')}번 칸.")
    else:
        lines.append(f"{d.get('from')}번 칸에서 {d.get('to')}번 칸으로 이동.")
    if event.kind == "win":
        lines.append(f"{who}이 결승점에 도착해 승리!")
    return " ".join(lines)


def _yut_facts(event: Event, who: str, d: dict) -> str:
    k = event.kind
    if k == "throw":
        text = f"{event.turn}턴 {who} 차례. 윷을 던져 '{d['yut']}'({d['value']}칸)이 나옴."
        return text + (" 한 번 더 던짐." if d.get("again") else "")
    if k == "move":
        dst = d["to"]
        text = f"{who}의 {d['piece']}번 말이 '{d['yut']}'로 {cell_name(d['from'])}에서 "
        text += "참먹이를 지나 완주." if dst == "goal" else f"{josa(cell_name(dst), '으로')} 이동."
        if d.get("stacked", 1) > 1:
            text += f" 업힌 말 {d['stacked']}개가 함께 움직임."
        return text
    if k == "capture":
        text = f"{who}이 {cell_name(d['cell'])}에서 상대 말 {d['captured']}개를 잡아 대기 칸으로 돌려보냄."
        return text + (" 잡았으니 한 번 더 던짐." if d.get("again") else "")
    if k == "stack":
        return f"{who}의 말 {d['stacked']}개가 {cell_name(d['cell'])}에서 업힘. 이제 함께 움직임."
    if k == "finish":
        return f"{who}의 말 {d['pieces']}개가 완주. 남은 말 {d['left']}개."
    if k == "decision":
        return f"로봇이 {d['piece']}번 말을 고름. 이유: {REASON_TEXT.get(d.get('reason'), d.get('reason'))}."
    if k == "win":
        return f"{who}이 말을 모두 완주시켜 {d.get('turns', event.turn)}턴 만에 승리!"
    return f"{event.turn}턴 {who}: {k} {d}"


def template(event: Event) -> str:
    """정해진 문장 틀로 중계합니다."""
    d = event.detail
    who = player_name(event.player)
    if event.kind == "help":
        return f"잠시만요! {d.get('message', '도움이 필요합니다')}"
    if is_yut(event):
        return _yut_template(event, who, d)
    if event.kind == "win":
        return random.choice([
            f"{who} 승리! 주사위 {d.get('dice')}로 결승점에 도착했습니다!",
            f"경기 끝! {who}이 {d.get('to')}번 칸 결승점에 먼저 도착했습니다!",
        ])
    info = d.get("event") or {}
    if info:
        return f"{who}, 주사위 {d.get('dice')}! 이벤트 칸 '{event_text(info)}'로 {d.get('to')}번 칸에 섭니다."
    return random.choice([
        f"{who}, 주사위 {d.get('dice')}! {d.get('from')}번 칸에서 {d.get('to')}번 칸으로 갑니다.",
        f"{who}이 {d.get('dice')}칸 전진해 {d.get('to')}번 칸에 도착!",
    ])


def _yut_template(event: Event, who: str, d: dict) -> str:
    k = event.kind
    if k == "throw":
        yut = d["yut"]
        if d.get("again"):
            return random.choice([f"{yut}! {who}, 한 번 더 던집니다!", f"와, {josa(yut, '이가')} 나왔어요! 한 번 더!"])
        return random.choice([f"{who}, {yut}! {d['value']}칸 갑니다.", f"{josa(yut, '이가')} 나왔습니다. {d['value']}칸!"])
    if k == "move":
        n = d.get("stacked", 1)
        subj = f"{who}의 업힌 말 {n}개가" if n > 1 else f"{who}의 말이"
        if d["to"] == "goal":
            return f"{subj} 참먹이를 지나 완주합니다!"
        place = josa(cell_name(d["to"]), "으로")
        if d["to"] in ("cell_5", "cell_10", "center"):
            return f"{subj} {place}! 다음엔 지름길을 탈 수 있어요."
        return random.choice([f"{who}, {d['yut']}! {subj} {place} 갑니다.", f"{subj} {place} 이동!"])
    if k == "capture":
        text = f"잡았다! {who}이 {cell_name(d['cell'])}에서 상대 말을 잡았습니다!"
        if d["captured"] > 1:
            text = f"한꺼번에 {d['captured']}개! {who}이 업힌 말을 통째로 잡았습니다!"
        return text + (" 한 번 더!" if d.get("again") else "")
    if k == "stack":
        return random.choice([f"{who}, 말 {d['stacked']}개를 업었습니다!", f"업었다! {who}의 말이 {cell_name(d['cell'])}에서 하나가 됩니다."])
    if k == "finish":
        if d["left"]:
            return f"{who}의 말이 완주! 이제 {d['left']}개 남았습니다."
        return f"{who}의 마지막 말까지 완주!"
    if k == "decision":
        return f"로봇은 {d['piece']}번 말을 골랐어요. {REASON_TEXT.get(d.get('reason'), '')}요."
    if k == "win":
        return random.choice([f"경기 끝! {who} 승리!", f"{who}이 {d.get('turns', event.turn)}턴 만에 이겼습니다!"])
    return facts(event)


PRIORITY = ["win", "capture", "finish", "stack", "move", "throw", "decision", "help"]


def headline(events: list[Event]) -> Event:
    """한 턴의 이벤트 중 가장 중계할 만한 것 (템플릿 대체 문장용)."""
    return min(events, key=lambda e: (PRIORITY.index(e.kind) if e.kind in PRIORITY else 99, -events.index(e)))
