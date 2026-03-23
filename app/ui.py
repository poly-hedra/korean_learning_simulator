"""Gradio 기반 로컬 웹 UI.

실행:
        python app/ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import gradio as gr

try:
    from app.orchestrator import orchestrator
except ModuleNotFoundError:
    # `python app/ui.py`로 실행할 때 프로젝트 루트를 import 경로에 추가
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.orchestrator import orchestrator


UI_CSS = """
.gradio-container {
    font-size: 18px !important;
}
.gradio-container h1,
.gradio-container h2,
.gradio-container h3 {
    font-size: 1.25em !important;
}
.gr-button {
    font-size: 18px !important;
    padding-top: 10px !important;
    padding-bottom: 10px !important;
}
.gr-textbox textarea,
.gr-textbox input,
.gr-dropdown,
.gr-radio,
.gr-checkbox {
    font-size: 17px !important;
}
.location-card {
    border: 1px solid #d7d7d7;
    border-radius: 12px;
    padding: 12px;
    background: #fafafa;
}
.location-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}
"""


def _format_personas(personas: dict[str, dict[str, Any]]) -> str:
    # 페르소나 필드 변경 반영: job→role, goal→mission
    lines: list[str] = []
    for role in ["A", "B"]:
        p = personas.get(role, {})
        lines.append(
            (
                f"[{role}] 이름: {p.get('name', '')} | 역할: {p.get('role', '')} | "
                f"나이: {p.get('age', '')} | 성별: {p.get('gender', '')} | 목표: {p.get('mission', '')}"
            )
        )
    return "\n".join(lines)


def _to_chat_messages(conversation_log: list[dict[str, Any]]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    for turn in conversation_log:
        speaker = turn.get("speaker", "")
        name = turn.get("name", "")
        utterance = turn.get("utterance", "")
        text = f"{name}: {utterance}" if name else utterance

        if speaker == "user":
            messages.append({"role": "user", "content": text})
        elif speaker == "ai":
            messages.append({"role": "assistant", "content": text})

    return messages


def _location_art_html(location: str) -> str:
    images = {
        "지하철2호선": """
<svg width="100%" viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="skySubway" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#f8fbff"/>
            <stop offset="100%" stop-color="#dce9ff"/>
        </linearGradient>
        <linearGradient id="bodySubway" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#8bb6ff"/>
            <stop offset="100%" stop-color="#3f79de"/>
        </linearGradient>
        <filter id="shadowSubway" x="-20%" y="-20%" width="140%" height="160%">
            <feDropShadow dx="0" dy="5" stdDeviation="4" flood-color="#223861" flood-opacity="0.35"/>
        </filter>
    </defs>
    <rect width="600" height="220" fill="url(#skySubway)"/>
    <ellipse cx="300" cy="178" rx="250" ry="24" fill="#9ab4dd" opacity="0.35"/>
    <g filter="url(#shadowSubway)">
        <rect x="45" y="52" width="510" height="112" rx="20" fill="url(#bodySubway)"/>
        <rect x="68" y="76" width="464" height="66" rx="12" fill="#dff0ff"/>
        <rect x="80" y="86" width="108" height="46" rx="7" fill="#bcd6fb"/>
        <rect x="200" y="86" width="108" height="46" rx="7" fill="#bcd6fb"/>
        <rect x="320" y="86" width="108" height="46" rx="7" fill="#bcd6fb"/>
        <rect x="440" y="86" width="80" height="46" rx="7" fill="#bcd6fb"/>
    </g>
    <circle cx="130" cy="165" r="18" fill="#2f3b52"/>
    <circle cx="470" cy="165" r="18" fill="#2f3b52"/>
    <circle cx="130" cy="165" r="8" fill="#9aa7bf"/>
    <circle cx="470" cy="165" r="8" fill="#9aa7bf"/>
    <text x="300" y="45" font-size="26" text-anchor="middle" fill="#2a3550">2호선 지하철</text>
</svg>
""",
        "한강": """
<svg width="100%" viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="skyRiver" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#d8eeff"/>
            <stop offset="100%" stop-color="#f5fbff"/>
        </linearGradient>
        <linearGradient id="waterRiver" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#5fc3f1"/>
            <stop offset="100%" stop-color="#2f8fcd"/>
        </linearGradient>
    </defs>
    <rect width="600" height="220" fill="url(#skyRiver)"/>
    <circle cx="520" cy="45" r="24" fill="#ffd369"/>
    <ellipse cx="520" cy="45" rx="32" ry="10" fill="#ffd369" opacity="0.25"/>
    <path d="M0 128 C115 106, 240 154, 360 129 C454 111, 525 150, 600 131 L600 220 L0 220 Z" fill="url(#waterRiver)"/>
    <path d="M0 146 C120 123, 250 165, 360 145 C470 129, 530 161, 600 149" stroke="#a9e5ff" stroke-width="3" fill="none" opacity="0.7"/>
    <rect x="0" y="168" width="600" height="52" fill="#8fc67b"/>
    <path d="M50 168 L125 168 L90 132 Z" fill="#6aaa5c"/>
    <path d="M500 168 L570 168 L540 138 Z" fill="#6aaa5c"/>
    <text x="300" y="42" font-size="26" text-anchor="middle" fill="#2a3550">한강</text>
</svg>
""",
        "명동": """
<svg width="100%" viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="skyMyeong" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ffe6d5"/>
            <stop offset="100%" stop-color="#fff6ef"/>
        </linearGradient>
        <linearGradient id="roadMyeong" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#b5b5b5"/>
            <stop offset="100%" stop-color="#8f8f8f"/>
        </linearGradient>
    </defs>
    <rect width="600" height="220" fill="url(#skyMyeong)"/>
    <polygon points="70,160 180,160 180,72 70,90" fill="#ffb347"/>
    <polygon points="180,160 205,148 205,62 180,72" fill="#e89d38"/>
    <polygon points="210,160 340,160 340,50 210,72" fill="#ff7f50"/>
    <polygon points="340,160 365,148 365,40 340,50" fill="#e2683f"/>
    <polygon points="370,160 520,160 520,65 370,82" fill="#ff9aa2"/>
    <polygon points="520,160 548,150 548,55 520,65" fill="#e67f88"/>
    <rect x="0" y="160" width="600" height="60" fill="url(#roadMyeong)"/>
    <path d="M0 188 L600 174" stroke="#dedede" stroke-width="3" stroke-dasharray="10 8"/>
    <text x="300" y="42" font-size="26" text-anchor="middle" fill="#2a3550">명동 거리</text>
</svg>
""",
        "올림픽공원": """
<svg width="100%" viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="skyPark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#daf3dc"/>
            <stop offset="100%" stop-color="#f6fff4"/>
        </linearGradient>
        <radialGradient id="treeA" cx="35%" cy="30%" r="70%">
            <stop offset="0%" stop-color="#9ee889"/>
            <stop offset="100%" stop-color="#4e9e43"/>
        </radialGradient>
        <radialGradient id="treeB" cx="40%" cy="30%" r="70%">
            <stop offset="0%" stop-color="#8fe091"/>
            <stop offset="100%" stop-color="#3f8d55"/>
        </radialGradient>
    </defs>
    <rect width="600" height="220" fill="url(#skyPark)"/>
    <path d="M0 150 C140 130, 260 170, 600 145 L600 220 L0 220 Z" fill="#78c47d"/>
    <ellipse cx="140" cy="168" rx="62" ry="14" fill="#4d8652" opacity="0.35"/>
    <ellipse cx="430" cy="170" rx="68" ry="16" fill="#4d8652" opacity="0.35"/>
    <circle cx="150" cy="116" r="48" fill="url(#treeA)"/>
    <rect x="142" y="121" width="16" height="46" fill="#7a5c3e"/>
    <circle cx="430" cy="110" r="54" fill="url(#treeB)"/>
    <rect x="421" y="118" width="18" height="50" fill="#7a5c3e"/>
    <text x="300" y="42" font-size="26" text-anchor="middle" fill="#2a3550">올림픽공원</text>
</svg>
""",
        "편의점": """
<svg width="100%" viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="skyStore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#e9eeff"/>
            <stop offset="100%" stop-color="#f9f9ff"/>
        </linearGradient>
        <linearGradient id="storeFront" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ffffff"/>
            <stop offset="100%" stop-color="#ececf4"/>
        </linearGradient>
    </defs>
    <rect width="600" height="220" fill="url(#skyStore)"/>
    <polygon points="105,180 500,180 470,52 130,52" fill="url(#storeFront)" stroke="#5b5b7a"/>
    <polygon points="130,52 470,52 488,42 145,42" fill="#5a6ccf"/>
    <rect x="132" y="58" width="336" height="26" fill="#56cc9d"/>
    <rect x="146" y="96" width="136" height="62" fill="#d9ebff" stroke="#a9bfdc"/>
    <rect x="312" y="90" width="142" height="76" fill="#f7f7f7" stroke="#cccccc"/>
    <rect x="356" y="92" width="30" height="74" fill="#d5d5d5"/>
    <ellipse cx="300" cy="190" rx="180" ry="16" fill="#8f93a1" opacity="0.3"/>
    <text x="300" y="42" font-size="26" text-anchor="middle" fill="#2a3550">편의점</text>
</svg>
""",
    }
    svg = images.get(location, images["명동"])
    return f"""
<div class=\"location-card\">
    <div class=\"location-title\">선택 장소: {location}</div>
    {svg}
</div>
"""


def start_session_ui(
    user_id: str,
    country: str,
    level: str,
    media_exp: bool,
    location: str,
) -> tuple[str, str, str, list[list[str]], str, bool, bool]:
    try:
        state = orchestrator.start_session(
            user_id=user_id.strip() or "guest",
            country=country.strip() or "Not provided",
            korean_level=level,
            has_korean_media_experience=media_exp,
            location=location,
            selected_role=None,
        )
    except Exception as exc:  # UI에서는 예외를 메시지로 반환
        return "", "", f"세션 시작 실패: {exc}", [], "", False, False

    scenario = state.get("scenario_title", "")  # 구 "scenario" 키 → "scenario_title"로 변경
    personas = state.get("personas", {})
    personas_text = _format_personas(personas)

    return (
        scenario,
        personas_text,
        "세션 시작 완료. 역할(A/B)을 선택한 뒤 '역할 확정' 버튼을 눌러주세요.",
        [],
        state.get("user_profile", {}).get("user_id", user_id),
        False,
        False,
    )


def choose_role_ui(
    user_id: str,
    selected_role: str,
) -> tuple[list[list[str]], str, bool, bool]:
    try:
        state = orchestrator.select_role_and_opening(
            user_id=user_id,
            selected_role=selected_role,
        )
    except Exception as exc:
        return [], f"역할 선택 실패: {exc}", False, False

    chat_pairs = _to_chat_messages(state.get("conversation_log", []))
    return (
        chat_pairs,
        f"역할 {selected_role} 선택 완료. 이제 대화를 시작하세요.",
        True,
        False,
    )


def send_message_ui(
    user_id: str,
    role_ready: bool,
    conversation_finished: bool,
    message: str,
    chat_pairs: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str, str, bool, bool]:
    if not role_ready:
        return (
            chat_pairs,
            "",
            "먼저 역할을 확정하세요.",
            role_ready,
            conversation_finished,
        )

    if conversation_finished:
        return (
            chat_pairs,
            "",
            "이미 턴 제한에 도달했습니다. 마지막 AI 응답으로 대화를 종료하고 평가를 진행하세요.",
            role_ready,
            True,
        )

    user_message = (message or "").strip()
    if not user_message:
        return (
            chat_pairs,
            "",
            "메시지를 입력해주세요.",
            role_ready,
            conversation_finished,
        )

    try:
        state = orchestrator.continue_turn(user_id=user_id, user_input=user_message)
    except Exception as exc:
        return (
            chat_pairs,
            "",
            f"대화 처리 실패: {exc}",
            role_ready,
            conversation_finished,
        )

    new_pairs = _to_chat_messages(state.get("conversation_log", []))
    finished = bool(state.get("is_finished", False))
    status = (
        "턴 제한 도달. 평가 버튼을 눌러 결과를 확인하세요."
        if finished
        else "대화 진행 중"
    )
    return new_pairs, "", status, role_ready, finished


def evaluate_ui(user_id: str, week: int) -> tuple[str, str, str, str, int]:
    try:
        evaluated = orchestrator.evaluate_session(user_id=user_id, week=week)
    except Exception as exc:
        return "", "", "", f"평가 실패: {exc}", week

    total = evaluated.get("total_score_10", 0)
    tier = evaluated.get("tier", "")
    feedback = evaluated.get("feedback", "")
    summary = evaluated.get("llm_summary", "")
    return str(total), str(tier), feedback, summary, week + 1


def build_review_ui(user_id: str) -> tuple[str, list[dict], list[dict], int, int, int]:
    try:
        review = orchestrator.build_weekly_review(user_id=user_id)
    except Exception as exc:
        return f"복습 생성 실패: {exc}", [], [], 0, 0, 0

    quizzes = review.get("chosung_quiz", [])
    cards = review.get("flashcards", [])
    weak_count = len(review.get("selected_weak_sessions", []))

    status = (
        f"복습 생성 완료 | 약점 세션: {weak_count} | 초성 퀴즈: {len(quizzes)} | "
        f"플래시카드: {len(cards)}"
    )
    return status, quizzes, cards, 0, 0, 0


def show_quiz_ui(quizzes: list[dict], index: int) -> tuple[str, str]:
    updates = tuple(
        gr.update(value=f"{i + 1}. (선택지 없음)", interactive=False) for i in range(4)
    )
    if not quizzes:
        return "퀴즈가 없습니다.", "", *updates
    idx = max(0, min(index, len(quizzes) - 1))
    q = quizzes[idx]
    choices = q.get("choices", [])
    choice_lines = [f"{i + 1}. {c}" for i, c in enumerate(choices)]

    filled = []
    for i in range(4):
        if i < len(choices):
            filled.append(gr.update(value=f"{i + 1}. {choices[i]}", interactive=True))
        else:
            filled.append(gr.update(value=f"{i + 1}. (선택지 없음)", interactive=False))

    return q.get("question", ""), "\n".join(choice_lines), *filled


def submit_quiz_answer_ui(
    quizzes: list[dict],
    index: int,
    answer_no: int,
    score: int,
) -> tuple[str, int, int, str, str, dict, dict, dict, dict]:
    if not quizzes:
        updates = tuple(
            gr.update(value=f"{i + 1}. (선택지 없음)", interactive=False)
            for i in range(4)
        )
        return "퀴즈가 없습니다.", score, index, "", "", *updates

    idx = max(0, min(index, len(quizzes) - 1))
    q = quizzes[idx]
    choices = q.get("choices", [])
    selected = choices[answer_no - 1] if 1 <= answer_no <= len(choices) else None
    correct = q.get("answer")

    if selected == correct:
        score += 1
        result = f"정답입니다! 현재 점수: {score}/{len(quizzes)}"
    else:
        result = f"오답입니다. 정답: {correct} | 현재 점수: {score}/{len(quizzes)}"

    next_idx = min(idx + 1, len(quizzes) - 1)
    next_q, next_choices, b1, b2, b3, b4 = show_quiz_ui(quizzes, next_idx)
    return result, score, next_idx, next_q, next_choices, b1, b2, b3, b4


def choose_quiz_1_ui(
    quizzes: list[dict], index: int, score: int
) -> tuple[str, int, int, str, str, dict, dict, dict, dict]:
    return submit_quiz_answer_ui(quizzes, index, 1, score)


def choose_quiz_2_ui(
    quizzes: list[dict], index: int, score: int
) -> tuple[str, int, int, str, str, dict, dict, dict, dict]:
    return submit_quiz_answer_ui(quizzes, index, 2, score)


def choose_quiz_3_ui(
    quizzes: list[dict], index: int, score: int
) -> tuple[str, int, int, str, str, dict, dict, dict, dict]:
    return submit_quiz_answer_ui(quizzes, index, 3, score)


def choose_quiz_4_ui(
    quizzes: list[dict], index: int, score: int
) -> tuple[str, int, int, str, str, dict, dict, dict, dict]:
    return submit_quiz_answer_ui(quizzes, index, 4, score)


def show_card_ui(cards: list[dict], index: int, revealed: bool) -> tuple[str, str]:
    if not cards:
        return "플래시카드가 없습니다.", ""
    idx = max(0, min(index, len(cards) - 1))
    card = cards[idx]
    front = card.get("front", "")
    back = card.get("back", "")
    return front, back if revealed else "(정답 숨김)"


def toggle_reveal_ui(
    cards: list[dict],
    index: int,
    revealed: bool,
) -> tuple[bool, str, str]:
    new_revealed = not revealed
    front, back = show_card_ui(cards, index, new_revealed)
    return new_revealed, front, back


def move_card_ui(
    cards: list[dict],
    index: int,
    direction: int,
) -> tuple[int, bool, str, str, str]:
    if not cards:
        return 0, False, "플래시카드가 없습니다.", "", ""

    next_index = max(0, min(index + direction, len(cards) - 1))
    front, back = show_card_ui(cards, next_index, False)
    status = f"카드 {next_index + 1}/{len(cards)}"
    return next_index, False, status, front, back


def prev_card_ui(cards: list[dict], index: int) -> tuple[int, bool, str, str, str]:
    return move_card_ui(cards, index, -1)


def next_card_ui(cards: list[dict], index: int) -> tuple[int, bool, str, str, str]:
    return move_card_ui(cards, index, 1)


with gr.Blocks(title="Korean Learning Simulator", css=UI_CSS) as demo:
    gr.Markdown("## Korean Learning Simulator - Gradio UI")

    user_id_state = gr.State("guest")
    role_ready_state = gr.State(False)
    conversation_finished_state = gr.State(False)
    week_state = gr.State(1)
    quizzes_state = gr.State([])
    cards_state = gr.State([])
    quiz_index_state = gr.State(0)
    quiz_score_state = gr.State(0)
    card_index_state = gr.State(0)
    card_revealed_state = gr.State(False)

    with gr.Row():
        user_id = gr.Textbox(label="User ID", value="guest")
        country = gr.Textbox(label="Country", value="Korea")
        level = gr.Dropdown(
            label="Korean Level",
            choices=["Beginner", "Intermediate", "Advanced"],
            value="Beginner",
        )
        media_exp = gr.Checkbox(label="Korean drama/movie experience", value=True)

    with gr.Row():
        location = gr.Dropdown(
            label="Location",
            choices=["지하철2호선", "한강", "명동", "올림픽공원", "편의점"],
            value="명동",
        )
        start_btn = gr.Button("1) 세션 시작", variant="primary")

    location_art = gr.HTML(value=_location_art_html("명동"))

    scenario_box = gr.Textbox(label="Scenario", lines=4)
    personas_box = gr.Textbox(label="Personas", lines=4)
    status_box = gr.Textbox(label="Status", lines=2)

    with gr.Row():
        role = gr.Radio(label="Your Role", choices=["A", "B"], value="A")
        choose_role_btn = gr.Button("2) 역할 확정")

    chatbot = gr.Chatbot(label="Conversation", height=360)
    with gr.Row():
        msg = gr.Textbox(label="Message")
        send_btn = gr.Button("전송")

    eval_btn = gr.Button("3) 평가하기")
    with gr.Row():
        total_score_box = gr.Textbox(label="Total Score")
        tier_box = gr.Textbox(label="Tier")
    feedback_box = gr.Textbox(label="Feedback", lines=3)
    summary_box = gr.Textbox(label="LLM Summary", lines=3)

    review_btn = gr.Button("4) 복습 생성")
    review_status = gr.Textbox(label="Review Status", lines=2)

    with gr.Tab("초성 퀴즈"):
        quiz_q_box = gr.Textbox(label="문제", lines=2)
        quiz_choices_box = gr.Textbox(label="보기", lines=4)
        with gr.Row():
            quiz_choice_btn_1 = gr.Button("1. (선택지 없음)", interactive=False)
            quiz_choice_btn_2 = gr.Button("2. (선택지 없음)", interactive=False)
        with gr.Row():
            quiz_choice_btn_3 = gr.Button("3. (선택지 없음)", interactive=False)
            quiz_choice_btn_4 = gr.Button("4. (선택지 없음)", interactive=False)
        quiz_result_box = gr.Textbox(label="결과")

    with gr.Tab("플래시카드"):
        card_status = gr.Textbox(label="진행", value="카드 0/0")
        card_front = gr.Textbox(label="앞면", lines=2)
        card_back = gr.Textbox(label="뒷면", lines=2)
        with gr.Row():
            prev_card_btn = gr.Button("이전")
            reveal_card_btn = gr.Button("정답 보기/숨기기")
            next_card_btn = gr.Button("다음")

    start_btn.click(
        fn=start_session_ui,
        inputs=[user_id, country, level, media_exp, location],
        outputs=[
            scenario_box,
            personas_box,
            status_box,
            chatbot,
            user_id_state,
            role_ready_state,
            conversation_finished_state,
        ],
    )

    location.change(
        fn=_location_art_html,
        inputs=[location],
        outputs=[location_art],
    )

    choose_role_btn.click(
        fn=choose_role_ui,
        inputs=[user_id_state, role],
        outputs=[chatbot, status_box, role_ready_state, conversation_finished_state],
    )

    send_btn.click(
        fn=send_message_ui,
        inputs=[
            user_id_state,
            role_ready_state,
            conversation_finished_state,
            msg,
            chatbot,
        ],
        outputs=[
            chatbot,
            msg,
            status_box,
            role_ready_state,
            conversation_finished_state,
        ],
    )

    eval_btn.click(
        fn=evaluate_ui,
        inputs=[user_id_state, week_state],
        outputs=[total_score_box, tier_box, feedback_box, summary_box, week_state],
    )

    review_btn.click(
        fn=build_review_ui,
        inputs=[user_id_state],
        outputs=[
            review_status,
            quizzes_state,
            cards_state,
            quiz_index_state,
            quiz_score_state,
            card_index_state,
        ],
    ).then(
        fn=show_quiz_ui,
        inputs=[quizzes_state, quiz_index_state],
        outputs=[
            quiz_q_box,
            quiz_choices_box,
            quiz_choice_btn_1,
            quiz_choice_btn_2,
            quiz_choice_btn_3,
            quiz_choice_btn_4,
        ],
    ).then(
        fn=show_card_ui,
        inputs=[cards_state, card_index_state, card_revealed_state],
        outputs=[card_front, card_back],
    ).then(
        fn=lambda cards, idx: f"카드 {idx + 1}/{len(cards)}" if cards else "카드 0/0",
        inputs=[cards_state, card_index_state],
        outputs=[card_status],
    )

    quiz_choice_btn_1.click(
        fn=choose_quiz_1_ui,
        inputs=[quizzes_state, quiz_index_state, quiz_score_state],
        outputs=[
            quiz_result_box,
            quiz_score_state,
            quiz_index_state,
            quiz_q_box,
            quiz_choices_box,
            quiz_choice_btn_1,
            quiz_choice_btn_2,
            quiz_choice_btn_3,
            quiz_choice_btn_4,
        ],
    )

    quiz_choice_btn_2.click(
        fn=choose_quiz_2_ui,
        inputs=[quizzes_state, quiz_index_state, quiz_score_state],
        outputs=[
            quiz_result_box,
            quiz_score_state,
            quiz_index_state,
            quiz_q_box,
            quiz_choices_box,
            quiz_choice_btn_1,
            quiz_choice_btn_2,
            quiz_choice_btn_3,
            quiz_choice_btn_4,
        ],
    )

    quiz_choice_btn_3.click(
        fn=choose_quiz_3_ui,
        inputs=[quizzes_state, quiz_index_state, quiz_score_state],
        outputs=[
            quiz_result_box,
            quiz_score_state,
            quiz_index_state,
            quiz_q_box,
            quiz_choices_box,
            quiz_choice_btn_1,
            quiz_choice_btn_2,
            quiz_choice_btn_3,
            quiz_choice_btn_4,
        ],
    )

    quiz_choice_btn_4.click(
        fn=choose_quiz_4_ui,
        inputs=[quizzes_state, quiz_index_state, quiz_score_state],
        outputs=[
            quiz_result_box,
            quiz_score_state,
            quiz_index_state,
            quiz_q_box,
            quiz_choices_box,
            quiz_choice_btn_1,
            quiz_choice_btn_2,
            quiz_choice_btn_3,
            quiz_choice_btn_4,
        ],
    )

    reveal_card_btn.click(
        fn=toggle_reveal_ui,
        inputs=[cards_state, card_index_state, card_revealed_state],
        outputs=[card_revealed_state, card_front, card_back],
    )

    prev_card_btn.click(
        fn=prev_card_ui,
        inputs=[cards_state, card_index_state],
        outputs=[
            card_index_state,
            card_revealed_state,
            card_status,
            card_front,
            card_back,
        ],
    )

    next_card_btn.click(
        fn=next_card_ui,
        inputs=[cards_state, card_index_state],
        outputs=[
            card_index_state,
            card_revealed_state,
            card_status,
            card_front,
            card_back,
        ],
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
