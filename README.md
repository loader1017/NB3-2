 AI Git Commit & PR Generator CLI

Git의 변경 사항(`git status`, `git diff`)을 수집하여 AI API를 이용해 커밋 메시지 및 Pull Request(PR) 초안을 자동으로 생성해주는 Python CLI 도구입니다.

---

## 1. 주요 기능

- **Git 변경 사항 자동 수집**: `git status` 및 `git diff`를 분석하여 컨텍스트 제공
- **커밋 메시지 자동 생성 (`commit`)**: 50자 이내(최대 72자)의 제목 1줄 및 변경 사항 요약 본문 생성
- **PR 제목 및 본문 자동 생성 (`pr`)**: 필수 섹션 헤더(`## Why`, `## What`, `## How to Test`)를 포함한 PR 초안 작성
- **안전 모드 (`--safe-mode`)**: API Key, Email 등 민감 정보 자동 마스킹 및 과도한 diff 길이 제한(최대 200줄)
- **API 호출 제어**: 비용 절감을 위해 1회 실행당 AI API 호출을 최대 1회로 제한

---

## 2. 설치 및 개발 환경

- **Python 버전**: Python 3.10 이상
- **필수 라이브러리**: `requests`

```bash
pip install requests
```

---

## 3. 환경변수 설정

보안을 위해 API Key는 코드에 하드코딩하지 않고 환경변수로 관리합니다. 실행 전 터미널에 아래와 같이 환경변수를 설정해 주세요.

```bash
# AI API Key 설정 (필수)
export AI_API_KEY="sk-cody-your-api-key-here"

# Base URL 설정 (선택, 기본값: https://copa.codyssey.kr/v1)
export AI_BASE_URL="https://copa.codyssey.kr/v1"
```

---

## 4. 실행 및 옵션 안내

### (1) 커밋 메시지 자동 생성
```bash
python3 main.py commit
```

### (2) PR 제목 및 본문 자동 생성
```bash
python3 main.py pr
```

### (3) 주요 옵션
| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `--model` | 사용할 AI 모델 지정 | `gpt-5.4-mini` |
| `--temperature` | 생성 다양성 조절 | `0.3` |
| `--max-tokens` | 최대 응답 토큰 수 | `800` |
| `--base-url` | API Base URL 변경 | `https://copa.codyssey.kr/v1` |
| `--safe-mode` | 민감정보 마스킹 및 diff 제한 활성화 | `True` |

### (4) 옵션 적용 실행 예시
```bash
python3 main.py commit --model gpt-5.4-mini --temperature 0.2
```

---

## 5. 터미널 실행 로그 예시

### 1) 커밋 메시지 생성 (`python3 main.py commit`)

```text
ryusungeun@SungEuns-MacBook-Pro NB3-2 % python3 main.py commit

[INFO] Git status 수집 완료: 1개 파일 변경 감지
[INFO] Git diff 수집 완료: 0줄
[INFO] AI API 요청 중... (모델: gpt-5.4-mini, URL: https://copa.codyssey.kr/v1)
[INFO] AI API 호출 횟수: 1회 완료
[DONE] 커밋 메시지 생성 완료

============================================================
Commit Message
============================================================
feat: main.py 초기 추가

- main.py 파일을 새로 추가해 기본 실행 진입점을 마련함
- 향후 기능 구현을 위한 Python 메인 모듈 구조를 준비함
============================================================
```

### 2) PR 초안 생성 (`python3 main.py pr`)

```text
ryusungeun@SungEuns-MacBook-Pro NB3-2 % python3 main.py pr

[INFO] Git status 수집 완료: 1개 파일 변경 감지
[INFO] Git diff 수집 완료: 0줄
[INFO] 현재 브랜치: main
[INFO] AI API 요청 중... (모델: gpt-5.4-mini, URL: https://copa.codyssey.kr/v1)
[INFO] AI API 호출 횟수: 1회 완료
[DONE] PR 초안 생성 완료

============================================================
PR Title
============================================================
main.py 추가
============================================================
PR Body
============================================================
## Why
- 프로젝트에 새로운 Python 진입점 또는 실행 스크립트가 필요합니다.

## What
- `main.py` 파일을 새로 추가했습니다.
- 기본 실행 로직을 담을 수 있는 구조를 준비했습니다.

## How to Test
- `python3 main.py`를 실행해 파일이 정상적으로 동작하는지 확인합니다.
- 실행 시 에러 없이 종료되는지 확인합니다.
============================================================
```

### 3) 변경 사항이 없을 경우

```text
ryusungeun@SungEuns-MacBook-Pro NB3-2 % python3 main.py commit

[INFO] 변경 사항이 없습니다. 작업 흐름을 종료합니다.
```

---

## 6. 운영 관점 및 보안 정책 안내

### 1) 민감정보 보호 (Safe Mode)
- diff 내 포함될 수 있는 API Key, Secret Token, Email 등의 민감 패턴을 정규표현식 기반으로 사전 마스킹(`[MASKED_API_KEY]`) 처리 후 API로 전송합니다.
- 대용량 diff 전송 시 발생할 수 있는 토큰 과다 소비 및 정보 유출을 방지하기 위해 diff text를 최대 200줄로 자동 절삭합니다.

### 2) 비용 및 호출 제한
- 명령 1회당 **API 호출 횟수를 1회로 엄격히 제한**하여 불필요한 반복 호출과 비용 청구를 방지합니다.
- CLI 실행 화면에 실제 API 호출 횟수 및 사용된 모델 정보가 투명하게 로그로 기록됩니다.

### 3) `max_tokens` 토큰 제한 및 응답 절단 위험 안내
- **절단 위험**: `max_tokens`(기본값 800) 상한 설정으로 인해 변경 내용이 매우 많거나 복잡할 경우 AI 응답이 작성 도중 잘릴 수 있습니다.
- **대처 방법**:
  1. `git add` 시 변경 단위별로 수량을 나누어 소규모 커밋/PR 단위로 분할 조작합니다.
  2. 필요시 CLI 실행 옵션으로 `--max-tokens 1500`과 같이 상한값을 상향 조정합니다.

### 4) 재생성(Retry) 대신 파이썬 후처리(Trimming) 방식 선택 이유 (Trade-off 분석)
본 도구는 규칙 미준수 시 API를 재호출(Retry)하는 대신, 파이썬 코드 기반의 후처리(`validate_and_trim_*`) 방식을 채택했습니다.

| 구분 | 후처리(Post-Processing) 방식 (채택) | AI 재생성(Retry) 방식 |
| --- | --- | --- |
| **비용/속도** | **최상** (1회 호출 보장, 즉시 응답) | **열악** (비용 및 대기시간 N배 증가) |
| **제어성** | **확실** (글자 수/필수 헤더 100% 보장) | **불확실** (재요청 시에도 규칙 미준수 가능) |
| **환각 위험** | **없음** (이미 생성된 텍스트 자르기/보완) | **있음** (재생성 시 내용 변질 가능) |

- **결론**: 실무에서의 지연 시간 최적화와 과도한 API 비용 발생 방지를 최우선으로 고려하여, 1회 호출 후 파이썬의 검증 및 트리밍 로직으로 응답 형식을 보장하는 방식을 적용했습니다.

### 5) AI 출력물의 수동 검토 필요성 및 체크리스트
AI가 생성한 커밋 메시지 및 PR 초안은 완전한 정답이 아니며, 환각(Hallucination)이나 문맥적 오류가 포함될 수 있습니다. **반드시 개발자가 수동 검토 후 적용**해야 합니다.

#### 📌 수동 검토 체크리스트
- [ ] **정확성**: 실제 변경하지 않은 기능이나 파일이 포함되어 있지 않은가?
- [ ] **누락 여부**: 핵심 변경사항(Bug Fix, Breaking Change 등)이 누락되지 않았는가?
- [ ] **보안 점검**: 마스킹되지 않은 기밀 데이터나 개인정보가 본문에 남아있지 않은가?
- [ ] **명확성**: 팀원 및 외부 리뷰어가 이해하기 적절한 표현과 톤으로 작성되었는가?
