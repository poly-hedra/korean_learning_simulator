"""FastAPI 애플리케이션 진입점."""

import argparse
import os

from fastapi import FastAPI
import gradio as gr

from api.conversation_router import router as conversation_router
from api.evaluation_router import router as evaluation_router
from api.review_router import router as review_router
from app.config import settings
from app.orchestrator import orchestrator
from app.ui import demo as gradio_demo

app = FastAPI(title=settings.app_name)
app.include_router(conversation_router)
app.include_router(evaluation_router)
app.include_router(review_router)
app = gr.mount_gradio_app(app, gradio_demo, path="/ui")


@app.get("/")
def health() -> dict:
    return {
        "service": settings.app_name,
        "model": settings.llm_model,
        "status": "ok",
    }


def _select_from_menu(title: str, options: list[str]) -> str:
    """터미널에 번호 메뉴를 표시하고 선택값을 반환한다."""

    print(f"\n{title}")
    for idx, item in enumerate(options, start=1):
        print(f"{idx}. {item}")

    while True:
        raw = input("Enter a number(번호를 입력하세요): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("Invalid input. Please try again.(잘못된 입력입니다. 다시 입력해주세요.)")


def _render_emoji_progress_bar(pct: int, width: int = 20) -> str:
    """사용자 요청 글리프로 이모지 진행 바를 렌더링한다."""

    safe_pct = max(0, min(100, pct))
    filled = round(width * safe_pct / 100)
    return f"{'🟩' * filled}{'⬛️' * (width - filled)} {safe_pct}%"


def _run_terminal_mode() -> None:
    """첫 방문 사용자 정보 수집과 장소 선택을 위한 대화형 터미널 흐름.

    사용자 요청처럼 서비스 첫 진입 시점에 장소를 바로 고를 수 있도록
    터미널 기반 온보딩 UI를 제공합니다.
    """

    print("=" * 60)
    print("Welcome to Korean DAEWHA Hunters!")
    print("=" * 60)

    user_id = input("Enter your user ID: ").strip() or "guest"
    country = input("Enter your country: ").strip() or "Not provided"

    korean_level = _select_from_menu(
        "Select your Korean level",
        ["Beginner", "Intermediate", "Advanced"],
    )

    media_raw = (
        input("Have you watched Korean dramas/movies before? (y/n): ").strip().lower()
    )
    has_korean_media_experience = media_raw in {"y", "yes", "1", "true", "네"}

    location_options = [
        "지하철2호선",
        "한강",
        "명동",
        "올림픽공원",
        "편의점",
    ]

    week = 1
    while True:
        print(f"\n=== Conversation Session {week} Start(대화 세션 {week} 시작) ===")
        location = _select_from_menu(
            "Select a conversation location(대화 장소를 선택하세요)",
            location_options,
        )

        started = orchestrator.start_session(
            user_id=user_id,
            country=country,
            korean_level=korean_level,
            has_korean_media_experience=has_korean_media_experience,
            location=location,
            selected_role=None,
        )

        print("\n[Scenario(시나리오)]")
        print(started.get("scenario_title", ""))  # 구 "scenario" 키 → "scenario_title"로 변경

        print("\n[Participants(대화 참여자 설정)]")
        personas = started.get("personas", {})
        for role in ["A", "B"]:
            persona = personas.get(role, {})
            print(
                # 페르소나 필드 변경 반영: job→role, goal→mission
                f"{role}: Name={persona.get('name', '')}, Role={persona.get('role', '')}, "
                f"Age={persona.get('age', '')}, Gender={persona.get('gender', '')}, "
                f"Mission={persona.get('mission', '')}"
            )

        selected_role = _select_from_menu(
            "Select your role",
            ["A", "B"],
        )
        started = orchestrator.select_role_and_opening(
            user_id=user_id,
            selected_role=selected_role,
        )

        print("\n[AI Opening Message]")
        if started.get("conversation_log"):
            print(started["conversation_log"][-1].get("utterance", ""))

        print(
            "\nConversation starts now(대화를 시작합니다). To quit, enter '/exit' or '/종료'."
        )
        while True:
            try:
                user_input = input("YOU> ").strip()
            except EOFError:
                # 파이프 입력/비대화형 실행에서 입력 종료 시 정상 종료.
                print(
                    "\nInput ended, closing the program(입력이 종료되어 프로그램을 마칩니다)."
                )
                return

            if user_input in {"/종료", "/exit"}:
                break

            state = orchestrator.continue_turn(user_id=user_id, user_input=user_input)
            if (
                state.get("conversation_log")
                and state["conversation_log"][-1].get("speaker") == "ai"
            ):
                print(f"AI> {state['conversation_log'][-1].get('utterance', '')}")

            if state.get("is_finished"):
                print(
                    "\nTurn limit reached, ending this conversation(턴 제한에 도달해 대화를 종료합니다)."
                )
                break

        evaluated = orchestrator.evaluate_session(user_id=user_id, week=week)
        print("\n[Evaluation Result(평가 결과)]")
        print(f"Total Score(총점): {evaluated.get('total_score_10', 0)}/10")
        print(f"Tier(티어): {evaluated.get('tier', '')}")

        print("\n[Evaluation Feedback(평가 피드백)]")
        print(evaluated.get("feedback", ""))

        if evaluated.get("llm_summary"):
            print("\n[LLM Summary(LLM 요약)]")
            print(evaluated.get("llm_summary"))

        week += 1

        while True:
            print("\nChoose the next action(다음 동작을 선택하세요)")
            print("1. New Conversation(다시 대화하기)")
            print("2. Review(복습하기)")
            print("3. Exit(종료하기)")
            action = input("Enter a number(번호를 입력하세요): ").strip()

            if action == "1":
                break

            if action == "3":
                print("Exiting the program(프로그램을 종료합니다).")
                return

            if action != "2":
                print(
                    "Invalid input. Please enter 1, 2, or 3.(잘못된 입력입니다. 1, 2, 3 중에서 입력해주세요.)"
                )
                continue

            print("\n[Preparing Review(복습 준비 진행)]")
            review: dict = {}
            for step in orchestrator.build_weekly_review_with_progress(user_id=user_id):
                pct = int(step.get("pct", 0))
                msg = str(step.get("msg", ""))
                print(f"{_render_emoji_progress_bar(pct)} {msg}")
                if "review" in step:
                    review = step["review"]

            print("\n[Weekly Review Result(주간 복습 생성 결과)]")
            print(
                f"Weak Sessions(약점 세션 수): {len(review.get('selected_weak_sessions', []))}"
            )
            print(
                f"Cho-sung Quizzes(초성 퀴즈 수): {len(review.get('chosung_quiz', []))}"
            )
            print(f"Flashcards(플래시카드 수): {len(review.get('flashcards', []))}")

            quizzes = review.get("chosung_quiz", [])
            flashcards = review.get("flashcards", [])
            if not quizzes and not flashcards:
                print(
                    "\nNo review items are available. Please do another conversation first.(복습 항목이 없습니다. 다시 대화해서 세션을 누적해주세요.)"
                )
                continue

            while True:
                print("\nSelect a review type(복습 유형을 선택하세요):")
                print("1. Cho-sung Quiz(초성 퀴즈)")
                print("2. Flashcards(플래시카드)")
                print("3. Back(돌아가기)")
                sel = input("Enter a number(번호를 입력하세요): ").strip()

                if sel == "1":
                    if not quizzes:
                        print("No cho-sung quizzes available(초성 퀴즈가 없습니다).")
                        continue

                    print("\n[Cho-sung Quiz Start(초성 퀴즈 시작)]")
                    score = 0
                    for i, q in enumerate(quizzes, start=1):
                        print(f"\nProblem {i}: {q.get('question')}")
                        choices = q.get("choices", [])
                        for idx, choice in enumerate(choices, start=1):
                            print(f"  {idx}. {choice}")
                        ans = input(
                            "Enter the number of the correct answer(정답 번호를 입력하세요): "
                        ).strip()
                        try:
                            chosen = choices[int(ans) - 1]
                        except Exception:
                            print(
                                "Invalid input. Marking as incorrect.(잘못된 입력입니다. 오답으로 처리합니다.)"
                            )
                            chosen = None
                        if chosen == q.get("answer"):
                            print("Correct!(정답입니다!)")
                            score += 1
                        else:
                            print(
                                f"Incorrect. The correct answer is: {q.get('answer')}(오답입니다. 정답을 확인하세요.)"
                            )
                    print(
                        f"\nQuiz ended. Score(퀴즈 종료. 점수): {score}/{len(quizzes)}"
                    )
                elif sel == "2":
                    if not flashcards:
                        print("No flashcards available(플래시카드가 없습니다).")
                        continue

                    print("\n[Flashcard Study Start(플래시카드 학습 시작)]")
                    for i, card in enumerate(flashcards, start=1):
                        front = card.get("front")
                        back = card.get("back")
                        print(f"\nCard {i}: {front}")
                        input(
                            "Press Enter to reveal the answer(정답을 보려면 Enter를 누르세요)..."
                        )
                        print(f"{back}")
                    print(
                        "\nFlashcard review complete(플래시카드 복습이 완료되었습니다)"
                    )
                elif sel == "3":
                    break
                else:
                    print(
                        "Invalid selection. Please try again.(잘못된 선택입니다. 다시 시도해주세요.)"
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Korean Learning Agent runner")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run in FastAPI server mode(기본은 터미널 인터랙티브 모드)",
    )
    args = parser.parse_args()

    if args.serve:
        import uvicorn

        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run("main:app", host=host, port=port, reload=True)
    else:
        _run_terminal_mode()
