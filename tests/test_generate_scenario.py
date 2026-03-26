"""시나리오 생성 테스트 스크립트.

결과는 tests/results/ 에 JSON으로 저장된다.

실행:
    python tests/test_generate_scenario.py
    python tests/test_generate_scenario.py --location 명동 --runs 3
    python tests/test_generate_scenario.py --location 편의점 --runs 5
    python tests/test_generate_scenario.py --mode compare --runs 5   # 노드 방식 vs education_based 비교
"""

# `python tests/test_generate_scenario.py` 로 실행 시 Python이 스크립트 위치(tests/)를
# sys.path에 추가하기 때문에 상위 패키지(services 등)를 찾지 못한다.
# 아래 코드는 프로젝트 루트(korean_learning_simulator/)를 sys.path에 강제 추가한다.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import time
from datetime import datetime
from importlib import import_module
from pathlib import Path

from services.llm_service import llm_service
from tests.based_prompts.education_based import (
    build_system_prompt as eb_build_system_prompt,
    build_user_message as eb_build_user_message,
    clean_dialogue_functions as eb_clean_dialogue_functions,
)

build_location_context_prompt = import_module(
    "01_conversation.prompts.location_context"
).build_location_context_prompt

_scenario_module = import_module("01_conversation.prompts.scenario")
build_system_prompt = _scenario_module.build_system_prompt
build_user_message = _scenario_module.build_user_message
node_clean_dialogue_functions = _scenario_module.clean_dialogue_functions

RESULTS_DIR = Path(__file__).parent / "results"

LOC_CTX_TEMPERATURE = 0.9
SCENARIO_TEMPERATURE = 0.8


def run_once(location: str, level: str) -> dict:
    """location_context 노드 포함 전체 파이프라인 실행."""
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
    result["total_duration_s"] = round(result["location_context_duration_s"] + result["scenario_duration_s"], 2)
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
            cleaned = [f for f in node_clean_dialogue_functions(parsed["dialogue_function"]) if f]
            if cleaned:
                parsed["dialogue_function"] = cleaned
        result["scenario_parsed"] = parsed
    except Exception:
        result["scenario_parsed"] = None

    return result


def run_once_education_based(location: str, level: str) -> dict:
    """location_context 없이 education_based 프롬프트로 시나리오만 생성."""
    result: dict = {"location": location, "level": level, "location_context": None}

    t = time.perf_counter()
    raw = llm_service.generate_text(
        system_prompt=eb_build_system_prompt(),
        user_prompt=eb_build_user_message(location=location, level=level),
        temperature=SCENARIO_TEMPERATURE,
    )
    result["scenario_duration_s"] = round(time.perf_counter() - t, 2)
    result["total_duration_s"] = result["scenario_duration_s"]
    result["scenario_raw"] = raw

    try:
        end = raw.rfind("}")
        # LLM이 JSON을 두 번 출력하는 경우(오류 인지 후 재출력 등) 마지막 블록을 사용한다.
        # top-level {는 줄 앞에 바로 위치하므로 rfind("\n{")로 마지막 블록 시작점을 찾는다.
        last_start = raw.rfind("\n{")
        start = (last_start + 1) if last_start != -1 else raw.find("{")
        parsed = json.loads(raw[start : end + 1])
        if isinstance(parsed, dict) and "dialogue_function" in parsed:
            # node 방식과 동일한 이유로 후처리 적용.
            # education_based는 별도 clean 함수를 import하지만 로직은 동일하다.
            cleaned = [f for f in eb_clean_dialogue_functions(parsed["dialogue_function"]) if f]
            if cleaned:
                parsed["dialogue_function"] = cleaned
        result["scenario_parsed"] = parsed
    except Exception:
        result["scenario_parsed"] = None

    return result


def _print_result(label: str, result: dict) -> None:
    """터미널 출력. scenario_description을 강조해서 보여준다."""
    print(f"\n{'─'*60}")
    print(f"[{label}]")

    if result.get("location_context"):
        print(f"\n  location_context ({result['location_context_duration_s']}s)")
        print(f"  {result['location_context']}")

    parsed = result.get("scenario_parsed")
    if parsed:
        print(f"\n  scenario ({result['scenario_duration_s']}s)")
        desc = parsed.get("scenario_description", "")
        if desc:
            print(f"\n  ★ scenario_description: {desc}")
        print()
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(f"\n  [파싱 실패] ({result['scenario_duration_s']}s)")
        print(result["scenario_raw"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location", default="한강")
    parser.add_argument("--level", default="Beginner")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--mode",
        choices=["node", "education_based", "compare"],
        default="node",
        help="node: location_context 포함 / education_based: 하드코딩 어휘 기반 / compare: 둘 다 실행",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"scenario_{args.location}_{args.mode}_{timestamp}.json"

    output = {
        "meta": {
            "timestamp": timestamp,
            "model": llm_service.model_name,
            "mode": args.mode,
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
        print(f"Run {i+1}/{args.runs} | 장소: {args.location} | 수준: {args.level} | 모드: {args.mode}")
        print("="*60)

        entry: dict = {"run": i + 1}

        if args.mode in ("node", "compare"):
            node_result = run_once(location=args.location, level=args.level)
            node_result["run"] = i + 1
            entry["node"] = node_result
            _print_result("노드 방식 (location_context 포함)", node_result)

        if args.mode in ("education_based", "compare"):
            eb_result = run_once_education_based(location=args.location, level=args.level)
            eb_result["run"] = i + 1
            entry["education_based"] = eb_result
            _print_result("education_based (하드코딩 어휘 기반)", eb_result)

        if args.mode == "node":
            output["results"].append(entry["node"])
        elif args.mode == "education_based":
            output["results"].append(entry["education_based"])
        else:
            output["results"].append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"저장 완료: {filename}")


if __name__ == "__main__":
    main()
