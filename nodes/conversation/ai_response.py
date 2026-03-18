"""Conversation node: AI speaks first and then replies by turn."""

from prompts.conversation.prompt_templates import (
    AI_RESPONSE_OPENING_ROLE_A_TEMPLATE,
    AI_RESPONSE_OPENING_ROLE_B_TEMPLATE,
    AI_RESPONSE_SYSTEM_PROMPT_TEMPLATE,
    AI_RESPONSE_TURN_TEMPLATE,
)
from services.llm_service import llm_service
from states.conversation_state import ConversationState


def _guardrail_text(text: str) -> str:
    """Very small rule-based guardrail.

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
    scenario = state.get("scenario", "")
    user_input = state.get("user_input", "")
    conversation_log = state.get("conversation_log", [])

    # Build concise persona descriptions
    def persona_summary(p: dict) -> str:
        if not p:
            return ""
        parts = []
        if p.get("name"):
            parts.append(p.get("name"))
        if p.get("job"):
            parts.append(p.get("job"))
        if p.get("age"):
            parts.append(str(p.get("age")))
        if p.get("gender"):
            parts.append(p.get("gender"))
        if p.get("goal"):
            parts.append("goal:" + p.get("goal"))
        return ", ".join(parts)

    ai_summary = persona_summary(ai_persona)
    other_summary = persona_summary(other_persona)

    # Build dialogue history labeled by roles (A(이름)/B(이름)) so LLM can maintain role identity
    history_lines = []
    if conversation_log:
        for entry in conversation_log:
            utter = entry.get("utterance", "").strip()
            if not utter:
                continue
            # Prefer explicit role/name fields when present (added by user_response / ai_response)
            role_label = entry.get("role")
            name = entry.get("name")
            if role_label and name:
                history_lines.append(f"{role_label}({name}): {utter}")
                continue

            # Fallback behavior for older log entries
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

    # Compose user prompt containing scenario, persona summaries, recent history and current user input
    if not conversation_log:
        # initial AI opening (no prior turns)
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
    # append AI turn including role + name for consistent history labels
    state.setdefault("conversation_log", []).append(
        {
            "speaker": "ai",
            "role": ai_role,
            "name": ai_persona.get("name", "AI"),
            "utterance": ai_text,
        }
    )
    return state
