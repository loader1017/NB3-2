#!/usr/bin/env python3
"""
AI 기반 Git 커밋 메시지 및 PR 설명 자동 생성 CLI 도구
"""

import argparse
import os
import re
import subprocess
import sys
import requests

# Default Configuration (gpt-5.4-mini 및 Codyssey Base URL 적용)
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 800
DEFAULT_BASE_URL = "https://copa.codyssey.kr/v1"


# ----------------------------------------------------------------------
# 1. Git Utility Functions
# ----------------------------------------------------------------------
def run_git_command(args):
    """Git 명령어를 실행하고 결과를 반환합니다."""
    try:
        result = subprocess.run(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git 명령 실행 실패 ('git {' '.join(args)}'): {e.stderr.strip()}")
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] Git이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.")
        sys.exit(1)


def check_git_repo():
    """현재 디렉토리가 Git 저장소인지 확인합니다."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError:
        print("[ERROR] CLI 실행은 Git이 초기화된 프로젝트 루트 디렉토리에서 수행되어야 합니다.")
        sys.exit(1)


def get_git_status():
    """git status 결과를 가져옵니다."""
    return run_git_command(["status", "--short"])


def get_git_diff():
    """git diff 결과를 가져옵니다 (첫 커밋 전 예외 처리 포함)."""
    diff = run_git_command(["diff", "--cached"])
    if diff:
        return diff

    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        diff = run_git_command(["diff", "HEAD"])
    except subprocess.CalledProcessError:
        diff = run_git_command(["diff"])

    return diff


def get_current_branch():
    """현재 Git 브랜치명을 가져옵니다."""
    try:
        branch = run_git_command(["branch", "--show-current"])
        return branch if branch else "main"
    except Exception:
        return "main"


# ----------------------------------------------------------------------
# 2. Security & Safe Mode
# ----------------------------------------------------------------------
def apply_safe_mode(diff_text):
    """
    안전 모드: 민감정보 마스킹 및 diff 길이 제한을 적용합니다.
    """
    diff_text = re.sub(r'(sk-[a-zA-Z0-9_-]{20,})', '[MASKED_API_KEY]', diff_text)
    diff_text = re.sub(r'([a-zA-Z0-9_]*SECRET[a-zA-Z0-9_]*\s*[:=]\s*["\'])[^\'"\s]+(["\'])', r'\1[MASKED_SECRET]\2', diff_text, flags=re.IGNORECASE)
    diff_text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[MASKED_EMAIL]', diff_text)

    lines = diff_text.splitlines()
    if len(lines) > 200:
        lines = lines[:200]
        lines.append("\n... [Safe Mode: diff가 200줄을 초과하여 생략되었습니다] ...")
        diff_text = "\n".join(lines)

    return diff_text


# ----------------------------------------------------------------------
# 3. AI API Call Wrapper
# ----------------------------------------------------------------------
def call_ai_api(prompt, model, temperature, max_tokens, api_key, base_url):
    """AI API를 REST 방식으로 호출합니다."""
    # 특수문자 및 공백 제거
    clean_base_url = re.sub(r'[\[\]\(\)\s]', '', base_url).rstrip("/")

    # URL 중복 중첩(https://...https://...) 방지 처리
    if "http" in clean_base_url:
        # http(s):// 가 여러 번 들어간 경우 마지막 정합 URL 추출 또는 중복 제거
        matches = re.findall(r'https?://[^\s]+', clean_base_url)
        if matches:
            clean_base_url = matches[0].rstrip("/")

    if not clean_base_url.startswith("http"):
        clean_base_url = "https://" + clean_base_url

    url = f"{clean_base_url}/chat/completions"


    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "너는 Git 커밋 메시지 및 PR 설명을 작성해주는 전문 개발 보조 AI 도구이다."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    print(f"[INFO] AI API 요청 중... (모델: {model}, URL: {clean_base_url})")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            print(f"[ERROR] AI API 호출 실패 (Status {response.status_code}): {error_msg}")
            sys.exit(1)
        
        result = response.json()
        print("[INFO] AI API 호출 횟수: 1회 완료")
        return result["choices"][0]["message"]["content"].strip()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 네트워크 또는 API 연결 오류 발생: {e}")
        sys.exit(1)


# ----------------------------------------------------------------------
# 4. Prompt Engineering & Post-processing
# ----------------------------------------------------------------------
def generate_commit_message(diff_text, status_text, args, api_key, base_url):
    prompt = f"""
다음 Git status 및 diff 정보를 바탕으로 커밋 메시지를 생성해줘.

[Git Status]
{status_text}

[Git Diff]
{diff_text}

[작성 규칙]
1. 첫 번째 줄은 커밋 제목으로, 50자 이내(최대 72자)로 한 줄 작성해라. (예: feat: ..., fix: ...)
2. 커밋 본문은 필수 불릿 항목 1~2개 이상을 사용하여 핵심 변경사항을 요약해라.
3. 변경된 핵심 파일이나 모듈 이름을 1개 이상 언급해라.
4. 부가 설명 없이 실제 커밋 메시지 텍스트만 출력해라.
"""
    raw_output = call_ai_api(prompt, args.model, args.temperature, args.max_tokens, api_key, base_url)
    return validate_and_trim_commit(raw_output)


def validate_and_trim_commit(text):
    lines = text.strip().splitlines()
    if not lines:
        return text

    title = lines[0]
    if len(title) > 72:
        title = title[:69] + "..."
    lines[0] = title
    return "\n".join(lines)


def generate_pr_description(diff_text, status_text, branch_name, args, api_key, base_url):
    prompt = f"""
다음 Git 브랜치, status, diff 정보를 바탕으로 PR(Pull Request) 제목과 본문을 작성해줘.

[Current Branch]
{branch_name}

[Git Status]
{status_text}

[Git Diff]
{diff_text}

[작성 규칙]
1. PR 제목: 1줄, 최대 80자 이내로 작성해라.
2. PR 본문: 아래의 Markdown 헤더 섹션을 정확히 포함해야 한다.
## Why
## What
## How to Test
3. 각 섹션(Why, What, How to Test)에는 최소 1개 이상의 불릿('- ')이 포함되어야 한다.
4. 출력 형식은 첫 번째 줄에 PR 제목, 이어서 빈 줄 하나 후 PR 본문을 작성해라.
"""
    raw_output = call_ai_api(prompt, args.model, args.temperature, args.max_tokens, api_key, base_url)
    return validate_and_trim_pr(raw_output)


def validate_and_trim_pr(text):
    lines = text.strip().splitlines()
    if not lines:
        return text

    title = lines[0]
    if len(title) > 80:
        title = title[:77] + "..."
    lines[0] = title

    body = "\n".join(lines[1:]).strip()

    required_sections = ["## Why", "## What", "## How to Test"]
    for sec in required_sections:
        if sec not in body:
            body += f"\n\n{sec}\n- 변경 사항 참조"

    return f"{lines[0]}\n\n{body}"


# ----------------------------------------------------------------------
# 5. Main CLI Entrypoint
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Git diff 기반 커밋 메시지 및 PR 초안 자동 생성 도구"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령을 선택하세요 (commit, pr)")
    
    commit_parser = subparsers.add_parser("commit", help="커밋 메시지 자동 생성")
    pr_parser = subparsers.add_parser("pr", help="PR 제목 및 본문 자동 생성")

    for p in [commit_parser, pr_parser]:
        p.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"사용할 AI 모델 (기본값: {DEFAULT_MODEL})")
        p.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help=f"Temperature 설정 (기본값: {DEFAULT_TEMPERATURE})")
        p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help=f"Max Tokens 설정 (기본값: {DEFAULT_MAX_TOKENS})")
        p.add_argument("--base-url", type=str, default=os.getenv("AI_BASE_URL", DEFAULT_BASE_URL), help=f"Base URL 설정 (기본값: {DEFAULT_BASE_URL})")
        p.add_argument("--safe-mode", action="store_true", default=True, help="민감 정보 마스킹 및 diff 길이를 제한하는 안전 모드 (기본값: True)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 1. API Key 검증
    api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 또는 OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("설정 예시:")
        print("  export AI_API_KEY=\"YOUR_API_KEY\"")
        sys.exit(1)

    # 2. Git 저장소 검증
    check_git_repo()

    # 3. Git 정보 수집
    status_text = get_git_status()
    diff_text = get_git_diff()

    if not diff_text and not status_text:
        print("[INFO] 변경 사항이 없습니다. 작업 흐름을 종료합니다.")
        sys.exit(0)

    changed_files_count = len(status_text.splitlines()) if status_text else 0
    diff_lines_count = len(diff_text.splitlines()) if diff_text else 0
    print(f"[INFO] Git status 수집 완료: {changed_files_count}개 파일 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {diff_lines_count}줄")

    # 4. 안전 모드 적용
    if args.safe_mode:
        diff_text = apply_safe_mode(diff_text)

    # 5. 명령별 작업 수행
    base_url = args.base_url

    if args.command == "commit":
        commit_msg = generate_commit_message(diff_text, status_text, args, api_key, base_url)
        print("[DONE] 커밋 메시지 생성 완료\n")
        print("=" * 60)
        print("Commit Message")
        print("=" * 60)
        print(commit_msg)
        print("=" * 60)

    elif args.command == "pr":
        branch_name = get_current_branch()
        print(f"[INFO] 현재 브랜치: {branch_name}")
        pr_text = generate_pr_description(diff_text, status_text, branch_name, args, api_key, base_url)
        
        pr_lines = pr_text.splitlines()
        pr_title = pr_lines[0] if pr_lines else ""
        pr_body = "\n".join(pr_lines[1:]).strip() if len(pr_lines) > 1 else ""

        print("[DONE] PR 초안 생성 완료\n")
        print("=" * 60)
        print("PR Title")
        print("=" * 60)
        print(pr_title)
        print("=" * 60)
        print("PR Body")
        print("=" * 60)
        print(pr_body)
        print("=" * 60)


if __name__ == "__main__":
    main()
