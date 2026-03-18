"""FastAPI application entrypoint."""

import argparse
import os

from fastapi import FastAPI

from api.conversation_router import router as conversation_router
from api.evaluation_router import router as evaluation_router
from api.review_router import router as review_router
from app.config import settings
from app.main import orchestrator

app = FastAPI(title=settings.app_name)
app.include_router(conversation_router)
app.include_router(evaluation_router)
app.include_router(review_router)


@app.get("/")
def health() -> dict:
    return {
        "service": settings.app_name,
        "model": settings.llm_model,
        "status": "ok",
    }


def _select_from_menu(title: str, options: list[str]) -> str:
    """Render a numbered menu in terminal and return selected value."""

    print(f"\n{title}")
    for idx, item in enumerate(options, start=1):
        print(f"{idx}. {item}")

    while True:
        raw = input("번호를 입력하세요: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("잘못된 입력입니다. 다시 입력해주세요.")


def _render_progress_bar(pct: int, width: int = 24) -> str:
    """Render a fixed-width text progress bar."""

    safe_pct = max(0, min(100, pct))
    filled = round(width * safe_pct / 100)
    return f"[{'#' * filled}{'-' * (width - filled)}] {safe_pct}%"


def _run_terminal_mode() -> None:
    """Interactive terminal flow for first-time access and location selection.

    사용자 요청처럼 서비스 첫 진입 시점에 장소를 바로 고를 수 있도록
    터미널 기반 온보딩 UI를 제공합니다.
    """

    print("=" * 60)
    print("Korean Daewha Hunters에 오신 것을 환영합니다!")
    print("=" * 60)

    user_id = input("사용자 ID를 입력하세요: ").strip() or "guest"
    country = input("출신 국가를 입력하세요: ").strip() or "미입력"

    korean_level = _select_from_menu(
        "한국어 수준을 선택하세요", ["초급", "중급", "고급"]
    )

    media_raw = input("한국 드라마/영화 접한 경험이 있나요? (y/n): ").strip().lower()
    has_korean_media_experience = media_raw in {"y", "yes", "1", "true", "네"}

    location_options = [
        "지하철2호선",
        "한강 둔치",
        "명동",
        "올림픽공원",
        "편의점",
    ]
    location = _select_from_menu("대화 장소를 선택하세요", location_options)

    started = orchestrator.start_session(
        user_id=user_id,
        country=country,
        korean_level=korean_level,
        has_korean_media_experience=has_korean_media_experience,
        location=location,
        selected_role=None,
    )

    print("\n[시나리오]")
    print(started.get("scenario", ""))

    print("\n[대화 참여자 설정]")
    personas = started.get("personas", {})
    for role in ["A", "B"]:
        persona = personas.get(role, {})
        print(
            f"{role}: 이름={persona.get('name', '')}, 직업={persona.get('job', '')}, "
            f"나이={persona.get('age', '')}, 성별={persona.get('gender', '')}, "
            f"목표={persona.get('goal', '')}"
        )

    selected_role = _select_from_menu("플레이할 역할을 선택하세요", ["A", "B"])
    started = orchestrator.select_role_and_opening(
        user_id=user_id,
        selected_role=selected_role,
    )

    print("\n[AI 첫 발화]")
    if started.get("conversation_log"):
        print(started["conversation_log"][-1].get("utterance", ""))

    print("\n대화를 시작합니다. 종료하려면 '/종료'를 입력하세요.")
    while True:
        try:
            user_input = input("YOU> ").strip()
        except EOFError:
            # 파이프 입력/비대화형 실행에서 입력 종료 시 정상 종료.
            print("\n입력이 종료되어 대화를 마칩니다.")
            break

        if user_input in {"/종료", "/exit"}:
            break

        state = orchestrator.continue_turn(user_id=user_id, user_input=user_input)
        if (
            state.get("conversation_log")
            and state["conversation_log"][-1].get("speaker") == "ai"
        ):
            print(f"AI> {state['conversation_log'][-1].get('utterance', '')}")

        if state.get("is_finished"):
            print("\n턴 제한에 도달해 대화를 종료합니다.")
            break

    evaluated = orchestrator.evaluate_session(user_id=user_id, week=1)
    print("\n[평가 결과]")
    print(f"총점: {evaluated.get('total_score_10', 0)}/10")
    print(f"티어: {evaluated.get('tier', '')}")

    progress_completed = False
    if evaluated.get("progress_log"):
        print("\n[평가 진행]")
        for entry in evaluated.get("progress_log", []):
            pct = int(entry.get("pct", 0))
            print(f"{_render_progress_bar(pct)} {entry.get('msg', '')}")
            if pct >= 100:
                progress_completed = True

    if progress_completed or not evaluated.get("progress_log"):
        print("\n[평가 피드백]")
        print(evaluated.get("feedback", ""))

    if evaluated.get("llm_summary"):
        print("\n[LLM 요약]")
        print(evaluated.get("llm_summary"))

    review = orchestrator.build_weekly_review(user_id=user_id)
    print("\n[주간 복습 생성 결과]")
    print(f"약점 세션 수: {len(review.get('selected_weak_sessions', []))}")
    print(f"초성 퀴즈 수: {len(review.get('chosung_quiz', []))}")
    print(f"플래시카드 수: {len(review.get('flashcards', []))}")

    # 대화 종료 직후 초성 퀴즈가 있으면 사용자에게 실행 여부를 묻습니다.
    quizzes = review.get("chosung_quiz", [])
    flashcards = review.get("flashcards", [])
    if quizzes or flashcards:
        run_review = (
            input("\n복습 항목이 준비되어 있습니다. 복습을 하시겠습니까? (y/n): ")
            .strip()
            .lower()
        )
        if run_review in {"y", "yes", "네", "ㅇ", "1"}:
            while True:
                print("\nSelect a review type:")
                print("1. 초성 퀴즈(Cho-sung Quiz)")
                print("2. 플래시카드(Flashcards)")
                print("3. 그만하겠습니다(Exit)")
                sel = input("Enter the number: ").strip()

                if sel == "1":
                    if not quizzes:
                        print("초성 퀴즈가 없습니다.")
                        continue

                    print("\n[초성 퀴즈 시작(Cho-sung Quiz Start)]")
                    score = 0
                    for i, q in enumerate(quizzes, start=1):
                        print(f"\nProblem {i}: {q.get('question')}")
                        choices = q.get("choices", [])
                        for idx, choice in enumerate(choices, start=1):
                            print(f"  {idx}. {choice}")
                        ans = input("Enter the number of the correct answer: ").strip()
                        try:
                            chosen = choices[int(ans) - 1]
                        except Exception:
                            print("Invalid input. Marking as incorrect.")
                            chosen = None
                        if chosen == q.get("answer"):
                            print("Correct!")
                            score += 1
                        else:
                            print(
                                f"Incorrect. The correct answer is: {q.get('answer')}"
                            )
                    print(f"\nQuiz ended. Score: {score}/{len(quizzes)}")
                elif sel == "2":
                    if not flashcards:
                        print("플래시카드가 없습니다.")
                        continue

                    print("\n[플래시카드 학습 시작]")
                    for i, card in enumerate(flashcards, start=1):
                        front = card.get("front")
                        back = card.get("back")
                        print(f"\nCard {i}: {front}")
                        input("Press Enter to reveal the answer...")
                        print(f"{back}")
                    print("\nFlashcard review complete")
                elif sel == "3":
                    print("Ending review.")
                    break
                else:
                    print("Invalid selection. Please try again.")
        else:
            print("Skipping review.")
    else:
        print(
            "\nNo chosung quizzes/flashcards available. Please generate an evaluation session first."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Korean Learning Agent runner")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="FastAPI 서버 모드로 실행 (기본은 터미널 인터랙티브 모드)",
    )
    args = parser.parse_args()

    if args.serve:
        import uvicorn

        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run("main:app", host=host, port=port, reload=True)
    else:
        _run_terminal_mode()
