"""시나리오 결과 JSON → CSV 변환 스크립트.

구글 스프레드시트에 붙여넣기 위한 용도.

실행:
    python tests/parse_scenario_results.py
    python tests/parse_scenario_results.py --file tests/results/scenario_한강_xxx.json
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import csv
import json


RESULTS_DIR = Path(__file__).parent / "results"


def parse_entry(entry: dict) -> dict:
    """education_based 단독 결과 entry에서 CSV용 필드를 추출한다.

    compare 모드와 달리 entry 자체에 scenario_parsed가 직접 포함된다.
    (node / education_based 중첩 키 없음)
    """
    parsed = entry.get("scenario_parsed") or {}
    personas = parsed.get("personas") or {}
    a = personas.get("A") or {}
    b = personas.get("B") or {}

    return {
        "run": entry.get("run", ""),
        "relationship_type": parsed.get("relationship_type", ""),
        "dialogue_function": ", ".join(parsed.get("dialogue_function", [])),
        "scenario_title": parsed.get("scenario_title", ""),
        "scenario_description": parsed.get("scenario_description", ""),
        "A_name": a.get("name", ""),
        "A_role": a.get("role", ""),
        "A_mission": a.get("mission", ""),
        "B_name": b.get("name", ""),
        "B_role": b.get("role", ""),
        "B_mission": b.get("mission", ""),
        "scenario_duration_s": entry.get("scenario_duration_s", ""),
        "parse_ok": "O" if parsed else "X",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        help="결과 JSON 파일 경로 (없으면 최신 education_based 파일 자동 선택)",
    )
    args = parser.parse_args()

    if args.file:
        json_path = Path(args.file)
    else:
        files = sorted(
            RESULTS_DIR.glob("*education_based*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            print("education_based 결과 파일을 찾을 수 없습니다.")
            return
        json_path = files[0]
        print(f"파일 자동 선택: {json_path.name}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {})
    results = data.get("results", [])

    csv_path = json_path.with_suffix(".csv")

    fieldnames = [
        "run",
        "relationship_type",
        "dialogue_function",
        "scenario_title",
        "scenario_description",
        "A_name",
        "A_role",
        "A_mission",
        "B_name",
        "B_role",
        "B_mission",
        "scenario_duration_s",
        "parse_ok",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results:
            writer.writerow(parse_entry(entry))

    parse_fail = sum(1 for r in results if not r.get("scenario_parsed"))
    print(f"\n메타 정보:")
    print(f"  모델: {meta.get('model')}")
    print(f"  scenario_temperature: {meta.get('scenario_temperature')}")
    print(f"  장소: {meta.get('location')}")
    print(f"  레벨: {meta.get('level')}")
    print(f"  runs: {meta.get('runs')}")
    print(f"  파싱 실패: {parse_fail}건")
    print(f"\nCSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    main()
