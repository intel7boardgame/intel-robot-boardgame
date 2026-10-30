# 협업 규칙

## 브랜치

```
main        시연 가능한 상태만. 직접 push 금지, PR로만 병합
develop     통합 브랜치. 각자 작업을 여기로 PR
feature/*   기능 개발      예) feature/KAN-15-vision-read-yut
fix/*       버그 수정      예) fix/KAN-40-robot-grip-miss
docs/*      문서           예) docs/rules-v1
```

- 브랜치 이름에 **Jira 업무 키(KAN-○○)** 를 넣으면 Jira 업무 화면에 브랜치·커밋·PR이 자동으로 연결됩니다.
- `develop`에서 브랜치를 따고, 작업이 끝나면 `develop`으로 PR을 엽니다.
- Day 4(MVP), Day 9(최종)에 `develop` → `main`으로 병합합니다.

```bash
git switch develop
git pull
git switch -c feature/KAN-15-vision-read-yut
# 작업 후
git add .
git commit -m "feat(vision): KAN-15 윷 앞뒤 다수결 인식 추가"
git push -u origin feature/KAN-15-vision-read-yut
# GitHub에서 develop 대상으로 PR 생성
```

## 커밋 메시지

```
<유형>(<모듈>): <Jira 키> <한 줄 설명>
```

| 유형 | 쓰는 경우 |
|---|---|
| feat | 기능 추가 |
| fix | 버그 수정 |
| refactor | 동작 변경 없는 코드 정리 |
| docs | 문서 |
| test | 테스트 |
| chore | 설정, 의존성, 기타 |

모듈: `game` `vision` `robot` `llm` `db` `ui` `config` `scripts`

예) `fix(robot): KAN-22 7번 칸 집기 높이 수정`

## 폴더 담당

| 폴더 | 담당 |
|---|---|
| `src/game`, `src/common`, `config/rules.json` | 김동현 (C1) |
| `src/vision`, `config/slots.json` | 정성욱 (B) |
| `src/robot`, `config/poses.json` | 신이서 (A) |
| `src/llm`, `src/db`, `config/quiz.json`, `docs/rules.md` | 김관영 (C2) |
| `src/ui` | 김민범 (D) |

- 남의 폴더를 고칠 때는 PR에 담당자를 리뷰어로 지정합니다.
- `src/common/interfaces.py`(모듈 간 약속)를 바꿀 때는 전원에게 먼저 알립니다.

## git에 올리지 않는 것

이미지·녹화 데이터(`data/`), 모델·체크포인트(`models/`), 가상환경, `.env`. 모델은 Hugging Face Hub로 공유합니다.
