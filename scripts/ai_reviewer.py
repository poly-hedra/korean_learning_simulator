#!/usr/bin/env python3
"""
AI 코드 리뷰어 스크립트

PR의 변경사항을 분석하여 AI가 코드 리뷰를 수행합니다.
"""

import sys
import subprocess
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_pr_changes():
    """PR의 변경된 파일 목록을 가져옵니다."""
    try:
        # gh CLI를 사용하여 PR의 변경 파일 목록 가져오기
        result = subprocess.run(
            ["gh", "pr", "diff", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        changed_files = result.stdout.strip().split("\n")
        return [f for f in changed_files if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # gh CLI가 없거나 PR이 없는 경우 (로컬 테스트용)
        print(f"Warning: Could not get PR changes ({e}), using git diff instead")
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            changed_files = result.stdout.strip().split("\n")
            return [f for f in changed_files if f.strip()]
        except subprocess.CalledProcessError:
            return []


def get_file_diff(file_path):
    """특정 파일의 diff를 가져옵니다."""
    # gh CLI가 없는 경우 바로 git diff 사용
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", file_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def analyze_changes_with_ai(changes_summary):
    """AI를 사용하여 변경사항을 분석합니다."""
    try:
        from services.llm_service import LLMService

        llm_service = LLMService()

        prompt = f"""
다음은 Pull Request의 변경사항 요약입니다:

{changes_summary}

이 변경사항에 대해 코드 리뷰를 수행해주세요. 다음 사항들을 고려해주세요:

1. 코드 품질 및 스타일
2. 잠재적인 버그나 문제점
3. 개선 제안사항
4. 보안 고려사항
5. 성능 영향

리뷰 결과를 마크다운 형식으로 작성해주세요.
"""

        response = llm_service.generate_text("", prompt, temperature=0.3)
        return response

    except Exception as e:
        return f"AI 리뷰 생성 중 오류 발생: {str(e)}"


def main():
    """메인 함수"""
    print("🔍 AI 코드 리뷰 시작...")

    # PR 변경사항 가져오기
    changed_files = get_pr_changes()

    if not changed_files:
        return "### 🤖 AI 코드 리뷰\n\n변경된 파일이 없습니다."

    print(f"📁 변경된 파일 수: {len(changed_files)}")

    # 변경사항 요약 생성
    changes_summary = "## 변경된 파일 목록\n\n"
    for file_path in changed_files[:10]:  # 최대 10개 파일만 분석
        changes_summary += f"- `{file_path}`\n"

        # 파일 diff 가져오기 (너무 길면 생략)
        diff = get_file_diff(file_path)
        if diff and len(diff) < 2000:  # diff가 너무 길면 생략
            changes_summary += f"  ```diff\n{diff}\n  ```\n\n"

    changes_summary += "\n---\n"

    # AI 리뷰 생성
    ai_review = analyze_changes_with_ai(changes_summary)

    # 결과 출력
    result = f"""### 🤖 AI 코드 리뷰

**분석된 파일 수:** {len(changed_files)}

{ai_review}
"""

    print(result)
    return result


if __name__ == "__main__":
    result = main()
    print(result)
