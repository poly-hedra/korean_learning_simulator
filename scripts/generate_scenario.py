"""시나리오 생성 테스트 스크립트.

결과는 scripts/results/ 에 JSON으로 저장된다.

실행:
    python scripts/generate_scenario.py
    python scripts/generate_scenario.py --location 명동 --runs 3
    python scripts/generate_scenario.py --location 편의점 --runs 5
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import sys
import time
from datetime import datetime

from importlib import import_module

from app.infra.ai.service import llm_service

_scenario_module = import_module("app.domain.conversation.prompts.scenario")
build_system_prompt = _scenario_module.build_system_prompt
build_user_message = _scenario_module.build_user_message
VERSION = _scenario_module.VERSION

RESULTS_DIR = Path(__file__).parent / "results"

SCENARIO_TEMPERATURE = 0.8


def run_once(location: str, level: str) -> dict:
    """시나리오 생성 1회 실행."""

    result: dict = {"location": location, "level": level}

    started_at = time.perf_counter()
    raw = llm_service.generate_text(
        system_prompt=build_system_prompt(),
        user_prompt=build_user_message(location=location, level=level),
        temperature=SCENARIO_TEMPERATURE,
    )
    result["scenario_duration_s"] = round(time.perf_counter() - started_at, 2)
    result["scenario_raw"] = raw

    try:
        end = raw.rfind("}")
        last_start = raw.rfind("\n{")
        start = (last_start + 1) if last_start != -1 else raw.find("{")
        parsed = json.loads(raw[start : end + 1])
        if isinstance(parsed, dict) and "dialogue_function" in parsed:
            raw = parsed["dialogue_function"]
            if isinstance(raw, list):
                parsed["dialogue_function"] = raw[0] if raw else ""
        result["scenario_parsed"] = parsed
    except Exception:
        result["scenario_parsed"] = None

    return result


def _print_result(result: dict) -> None:
    """터미널에 실행 결과를 출력한다."""

    print(f"\n{'─' * 60}")
    parsed = result.get("scenario_parsed")
    if parsed:
        print(f"  scenario ({result['scenario_duration_s']}s)")
        description = parsed.get("scenario_description", "")
        if description:
            print(f"\n  ★ scenario_description: {description}")
        print()
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return

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

    for run_number in range(args.runs):
        print(f"\n{'=' * 60}")
        print(
            f"Run {run_number + 1}/{args.runs} | 장소: {args.location} | 수준: {args.level}"
        )
        print("=" * 60)

        result = run_once(location=args.location, level=args.level)
        result["run"] = run_number + 1
        _print_result(result)
        output["results"].append(result)

    with filename.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"저장 완료: {filename}")


if __name__ == "__main__":
    main()
