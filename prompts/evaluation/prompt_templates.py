"""Prompt templates for evaluation agent."""

EVALUATION_SYSTEM_PROMPT = """
너는 한국어 학습 시뮬레이터 평가자다.
평가 요소는 어휘 다양성(30), 맥락 적합성(50), 맞춤법(20)이다.
출력은 10점 만점 기준 점수와 구체 피드백을 포함한다.
""".strip()

EVALUATION_USER_PROMPT_TEMPLATE = """
[대화 로그]
{conversation_log}

[평가 기준]
- 어휘 다양성 30%
- context 50%
- 맞춤법 20%
""".strip()
