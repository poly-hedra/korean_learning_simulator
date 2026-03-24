"""시나리오 생성 테스트 스크립트.

결과는 tests/results/ 에 JSON으로 저장된다.

실행:
    python tests/test_generate_scenario.py
    python tests/test_generate_scenario.py --location 명동 --runs 3
    python tests/test_generate_scenario.py --location 편의점 --runs 5
"""

import argparse
import json
import time
from datetime import datetime
from importlib import import_module
from pathlib import Path

from services.llm_service import llm_service

build_location_context_prompt = import_module(
    "01_conversation.prompts.location_context"
).build_location_context_prompt

build_system_prompt = import_module("01_conversation.prompts.scenario").build_system_prompt
build_user_message = import_module("01_conversation.prompts.scenario").build_user_message

RESULTS_DIR = Path(__file__).parent / "results"

LOC_CTX_TEMPERATURE = 0.9
SCENARIO_TEMPERATURE = 0.8


def run_once(location: str, level: str) -> dict:
    result: dict = {"location": location, "level": level}

    # 1단계: location context
    t0 = time.perf_counter()
    context = llm_service.generate_text(
        system_prompt="너는 한국 문화와 장소에 정통한 현지인이다.",
        user_prompt=build_location_context_prompt(location),
        temperature=LOC_CTX_TEMPERATURE,
    )
    result["location_context_duration_s"] = round(time.perf_counter() - t0, 2)
    result["location_context"] = context.strip()

    # 2단계: 시나리오
    t1 = time.perf_counter()
    raw = llm_service.generate_text(
        system_prompt=build_system_prompt(level),
        user_prompt=build_user_message(
            location=location, korean_level=level, location_context=context
        ),
        temperature=SCENARIO_TEMPERATURE,
    )
    result["scenario_duration_s"] = round(time.perf_counter() - t1, 2)
    result["scenario_raw"] = raw

    # JSON 파싱
    try:
        start, end = raw.find("{"), raw.rfind("}")
        result["scenario_parsed"] = json.loads(raw[start : end + 1])
    except Exception:
        result["scenario_parsed"] = None

    return result


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
            "location_context_temperature": LOC_CTX_TEMPERATURE,
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
        output["results"].append(result)

        print(f"\n[location_context] ({result['location_context_duration_s']}s)")
        print(result["location_context"])

        parsed = result.get("scenario_parsed")
        if parsed:
            print(f"\n[scenario] ({result['scenario_duration_s']}s)")
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        else:
            print(f"\n[scenario - 파싱 실패] ({result['scenario_duration_s']}s)")
            print(result["scenario_raw"])

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"저장 완료: {filename}")


if __name__ == "__main__":
    main()
