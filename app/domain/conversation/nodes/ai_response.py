"""대화 노드: AI가 먼저 시작하고 턴마다 응답한다."""

from ..prompts.ai_response import (
    AI_RESPONSE_OPENING_ROLE_A_TEMPLATE,
    AI_RESPONSE_OPENING_ROLE_B_TEMPLATE,
    AI_RESPONSE_SYSTEM_PROMPT_TEMPLATE,
    AI_RESPONSE_TURN_TEMPLATE,
)
from app.infra.ai.service import llm_service
from ..state import ConversationState


def _guardrail_text(text: str) -> str:
    """간단한 규칙 기반 가드레일.

    ※ 주석 라인 제거, 과도한 길이 제한, 대화 목적과 무관한 내용 확장 완화.
    """
    # ※로 시작하는 줄(설명/주석)은 대화 발화가 아니므로 제거
    lines = [
        line.strip()
        for line in text.splitlines()
        if not line.strip().lstrip("-*• ").startswith("※")
    ]
    cleaned = " ".join(line for line in lines if line).strip()
    if not cleaned:
        cleaned = "좋아요. 계속 이야기해 볼까요?"
    if len(cleaned) > 220:
        cleaned = cleaned[:220] + "..."
    return cleaned


def ai_response(state: ConversationState) -> ConversationState:
    personas = state.get("personas", {})
    selected_role = state.get("user_profile", {}).get("selected_role", "A")
    ai_role = "B" if selected_role == "A" else "A"

    ai_persona = personas.get(ai_role, {})
    other_persona = personas.get(selected_role, {})
    user_input = state.get("user_input", "")
    conversation_log = state.get("conversation_log", [])

    location = state.get("location", "")
    relationship_type = state.get("relationship_type", "")
    dialogue_function = state.get("dialogue_function", [])
    scenario = (
        f"{relationship_type} 관계인 두 사람이 {location}에 함께 있다. "
        f"대화 목적은 {', '.join(dialogue_function)}이다."
    )

    # 간결한 페르소나 설명 구성
    def persona_summary(p: dict) -> str:
        if not p:
            return ""
        parts = []
        if p.get("name"):
            parts.append(p.get("name"))
        if p.get("role"):
            parts.append(p.get("role"))
        if p.get("age"):
            parts.append(str(p.get("age")))
        if p.get("gender"):
            parts.append(p.get("gender"))
        if p.get("mission"):
            parts.append("목표: " + p.get("mission"))
        return ", ".join(parts)

    ai_summary = persona_summary(ai_persona)
    other_summary = persona_summary(other_persona)

    # LLM이 역할 정체성을 유지하도록 역할 라벨(A(이름)/B(이름))로 대화 이력을 구성
    history_lines = []
    if conversation_log:
        for entry in conversation_log:
            utter = entry.get("utterance", "").strip()
            if not utter:
                continue
            # role/name 필드가 있으면 우선 사용 (user_response / ai_response에서 추가)
            role_label = entry.get("role")
            name = entry.get("name")
            if role_label and name:
                history_lines.append(f"{role_label}({name}): {utter}")
                continue

            # 이전 형식 로그 항목에 대한 대체 처리
            speaker = entry.get("speaker")
            if speaker == "user":
                role_label = selected_role or "A"
                name = personas.get(role_label, {}).get("name", "사용자")
                history_lines.append(f"{role_label}({name}): {utter}")
            else:
                role_label = ai_role
                name = ai_persona.get("name", "AI")
                history_lines.append(f"{role_label}({name}): {utter}")

    history_text = "\n".join(history_lines)

    # 강한 시스템 프롬프트로 역할 고정 + 한국어 사용 지시
    ai_name = ai_persona.get("name", ai_role)
    system_prompt = AI_RESPONSE_SYSTEM_PROMPT_TEMPLATE.format(
        ai_name=ai_name, ai_role=ai_role
    )

    # 시나리오, 페르소나 요약, 최근 대화 이력, 현재 사용자 입력을 포함한 사용자 프롬프트 구성
    if not conversation_log:
        # 첫 AI 시작 발화 (이전 턴 없음)
        tpl = (
            AI_RESPONSE_OPENING_ROLE_A_TEMPLATE
            if ai_role == "A"
            else AI_RESPONSE_OPENING_ROLE_B_TEMPLATE
        )
        prompt = tpl.format(
            scenario=scenario, ai_summary=ai_summary, other_summary=other_summary
        )
    else:
        prompt = AI_RESPONSE_TURN_TEMPLATE.format(
            scenario=scenario,
            ai_summary=ai_summary,
            other_summary=other_summary,
            history_text=history_text,
            user_input=user_input,
            ai_name=ai_name,
            ai_role=ai_role,
        )

    ai_text = llm_service.generate_text(
        system_prompt=system_prompt,
        user_prompt=prompt,
    )
    ai_text = _guardrail_text(ai_text)

    state["latest_ai_response"] = ai_text
    # 이력 라벨 일관성을 위해 role + name을 포함해 AI 턴을 추가
    state.setdefault("conversation_log", []).append(
        {
            "speaker": "ai",
            "role": ai_role,
            "name": ai_persona.get("name", "AI"),
            "utterance": ai_text,
        }
    )
    return state
