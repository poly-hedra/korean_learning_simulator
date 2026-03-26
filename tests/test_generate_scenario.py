"""시나리오 생성 테스트 스크립트.

결과는 tests/results/ 에 JSON으로 저장된다.

실행 (프로젝트 루트 korean_learning_simulator/ 에서):
    python -m tests.test_generate_scenario
    python -m tests.test_generate_scenario --location 명동 --runs 3
    python -m tests.test_generate_scenario --location 편의점 --runs 5

-m 플래그를 쓰는 이유:
    Python 인터프리터는 -m 실행 시 현재 디렉토리를 sys.path에 자동으로 추가한다.
    `python tests/test_xxx.py` 로 실행하면 tests/ 기준으로 패키지를 찾아서
    상위 패키지(services 등)를 못 찾는다. -m 을 쓰면 이 문제가 없다.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from services.llm_service import llm_service

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 동적 임포트를 함수로 이동
def load_scenario_module():
    from importlib import import_module
    _scenario_module = import_module("01_conversation.prompts.scenario")
    return _scenario_module

# 모듈 로드 및 전역 변수 할당
_scenario_module = load_scenario_module()
build_system_prompt = _scenario_module.build_system_prompt
build_user_message = _scenario_module.build_user_message
clean_dialogue_functions = _scenario_module.clean_dialogue_functions
VERSION = _scenario_module.VERSION

RESULTS_DIR = Path(__file__).parent / "results"

SCENARIO_TEMPERATURE = 0.8


def run_once(location: str, level: str) -> dict:
    """시나리오 생성 1회 실행."""
    result: dict = {"location": location, "level": level}

    t = time.perf_counter()
    raw = llm_service.generate_text(
        system_prompt=build_system_prompt(),
        user_prompt=build_user_message(location=location, level=level),
        temperature=SCENARIO_TEMPERATURE,
    )
    result["scenario_duration_s"] = round(time.perf_counter() - t, 2)
    result["scenario_raw"] = raw

    try:
        end = raw.rfind("}")
        # LLM이 JSON을 두 번 출력하는 경우(오류 인지 후 재출력 등) 마지막 블록을 사용한다.
        # top-level {는 줄 앞에 바로 위치하므로 rfind("\n{")로 마지막 블록 시작점을 찾는다.
        last_start = raw.rfind("\n{")
        start = (last_start + 1) if last_start != -1 else raw.find("{")
        parsed = json.loads(raw[start : end + 1])
        if isinstance(parsed, dict) and "dialogue_function" in parsed:
            # LLM이 "[각자 목표] 취향 묻기" 같이 카테고리 태그를 값에 포함하거나
            # "각자 목표" 처럼 카테고리명 자체를 출력하는 오류를 후처리로 정리한다.
            # cleaned가 빈 리스트면 원본을 그대로 유지한다(테스트 결과 보존 우선).
            cleaned = [f for f in clean_dialogue_functions(parsed["dialogue_function"]) if f]
            if cleaned:
                parsed["dialogue_function"] = cleaned
        result["scenario_parsed"] = parsed
    except Exception:
        result["scenario_parsed"] = None

    return result


def _print_result(result: dict) -> None:
    """터미널 출력. scenario_description을 강조해서 보여준다."""
    print(f"\n{'─'*60}")
    parsed = result.get("scenario_parsed")
    if parsed:
        print(f"  scenario ({result['scenario_duration_s']}s)")
        desc = parsed.get("scenario_description", "")
        if desc:
            print(f"\n  ★ scenario_description: {desc}")
        print()
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(f"  [파싱 실패] ({result['scenario_duration_s']}s)")
        print(result["scenario_raw"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location", default="한강")
    parser.add_argument("--level", default="Beginner")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"scenario_{args.location}_{timestamp}.json"

    output = {
        "meta": {
            "timestamp": timestamp,
            "model": llm_service.model_name,
            "scenario_temperature": SCENARIO_TEMPERATURE,
            "location": args.location,
            "level": args.level,
            "runs": args.runs,
        },
        "results": [],
    }

    for i in range(args.runs):
        print(f"\n{'='*60}")
        print(f"Run {i+1}/{args.runs} | 장소: {args.location} | 수준: {args.level}")
        print("="*60)

        result = run_once(location=args.location, level=args.level)
        result["run"] = i + 1
        _print_result(result)
        output["results"].append(result)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"저장 완료: {filename}")


if __name__ == "__main__":
    main()
