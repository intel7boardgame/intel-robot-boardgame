"""퀴즈 칸 (담당: 김관영, 확장). 문제를 내고 채점합니다.

정답이 틀리면 시연이 어색해지므로 문제와 정답은 config/quiz.json 은행에서 고르고,
LLM은 use_llm=True일 때 문제 문장을 다듬는 데만 씁니다. 채점은 코드가 합니다.
"""
import json
import random
from dataclasses import dataclass
from pathlib import Path

from llm.narrator import DEFAULT_MODEL, TIMEOUT, _make_client


@dataclass
class Quiz:
    question: str
    choices: list[str]
    answer: int  # choices 번호, 1부터

    def text(self) -> str:
        """화면·음성에 그대로 쓸 문제 문장."""
        options = "  ".join(f"{i}) {c}" for i, c in enumerate(self.choices, 1))
        return f"{self.question}  {options}"


class QuizMaster:
    def __init__(self, bank_path: Path, use_llm: bool = False, model: str = DEFAULT_MODEL,
                 client=None, seed: int | None = None):
        data = json.loads(Path(bank_path).read_text(encoding="utf-8"))
        self.bank = [Quiz(q["question"], q["choices"], q["answer"]) for q in data["questions"]]
        self.rng = random.Random(seed)
        self.used: set[int] = set()
        self.model = model
        self.client = client if client is not None else (_make_client(None, TIMEOUT) if use_llm else None)

    def ask(self) -> Quiz:
        """한 판 안에서는 같은 문제를 다시 내지 않습니다 (다 쓰면 처음부터)."""
        if len(self.used) >= len(self.bank):
            self.used.clear()
        i = self.rng.choice([i for i in range(len(self.bank)) if i not in self.used])
        self.used.add(i)
        quiz = self.bank[i]
        return Quiz(self._rephrase(quiz.question), quiz.choices, quiz.answer)

    @staticmethod
    def grade(quiz: Quiz, reply: str) -> bool:
        """'2', '2번', '모방학습'처럼 번호나 보기 글자로 답해도 채점합니다."""
        reply = reply.strip().rstrip("번").strip()
        if reply.isdigit():
            return int(reply) == quiz.answer
        return reply.replace(" ", "") == quiz.choices[quiz.answer - 1].replace(" ", "")

    def _rephrase(self, question: str) -> str:
        if self.client is None:
            return question
        try:
            reply = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content":
                           "아래 퀴즈 문제를 보드게임 진행자 말투로 한 문장으로 바꿔 써. "
                           f"뜻과 숫자는 그대로 두고 문장만 써.\n{question}"}],
                options={"temperature": 0.7, "num_predict": 60},
            )
            text = reply["message"]["content"].strip().replace("\n", " ")
        except Exception:
            return question
        return text if 0 < len(text) <= 100 else question
