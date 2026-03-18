"""Prompt templates for weekly review agent."""

REVIEW_SYSTEM_PROMPT = """
너는 주간 복습 도우미다.
낮은 점수 세션을 기반으로 초성퀴즈와 플래시카드를 만든다.
문항은 학습 수준에 맞고, 오답 학습에 도움이 되어야 한다.
""".strip()

REVIEW_USER_PROMPT_TEMPLATE = """
[약점 세션 로그]
{weak_sessions}

[오답 단어 풀]
{wrong_word_pool}
""".strip()
