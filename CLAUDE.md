# CLAUDE.md

이 저장소의 공통 안내는 AGENTS.md에 있습니다. 아래를 먼저 읽고 따릅니다.

@AGENTS.md

## Claude Code 추가 안내

- 답변과 커밋 메시지, 문서는 한국어로 씁니다.
- 작업 전에 관련 담당 폴더와 `docs/interfaces.md`를 먼저 읽고, 인터페이스를 건드리는 변경인지 확인합니다.
- 변경 후 `python src/main.py --mock`과 `python -m pytest tests`로 확인하고, 실행하지 못했다면 그 사실을 알립니다. `--mock`은 키보드 입력을 기다리므로 확인할 때는 `printf '6\n6\n6\n6\n6\n6\n6\n6\n' | python src/main.py --mock`처럼 입력을 넣어 실행합니다.
- Windows 환경에서 한글 출력이 깨지면 `PYTHONIOENCODING=utf-8`을 붙여 실행합니다.
- 실제 로봇이나 카메라를 쓰는 코드(`src/robot`, `src/vision`)는 실행하지 말고, 사람에게 실행을 요청합니다.
