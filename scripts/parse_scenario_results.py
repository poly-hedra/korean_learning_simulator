"""시나리오 결과 JSON → CSV 변환 스크립트."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import argparse
import csv
import json


RESULTS_DIR = Path(__file__).parent / "results"


def parse_entry(entry: dict) -> dict:
    """JSON 한 건을 CSV 행 구조로 변환한다."""

    parsed = entry.get("scenario_parsed") or {}
    personas = parsed.get("personas") or {}
    persona_a = personas.get("A") or {}
    persona_b = personas.get("B") or {}

    return {
        "run": entry.get("run", ""),
        "relationship_type": parsed.get("relationship_type", ""),
        "dialogue_function": parsed.get("dialogue_function", ""),
        "scenario_title": parsed.get("scenario_title", ""),
        "scenario_description": parsed.get("scenario_description", ""),
        "A_name": persona_a.get("name", ""),
        "A_role": persona_a.get("role", ""),
        "A_mission": persona_a.get("mission", ""),
        "B_name": persona_b.get("name", ""),
        "B_role": persona_b.get("role", ""),
        "B_mission": persona_b.get("mission", ""),
        "scenario_duration_s": entry.get("scenario_duration_s", ""),
        "parse_ok": "O" if parsed else "X",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        help="결과 JSON 파일 경로 (없으면 최신 scenario_*.json 파일 자동 선택)",
    )
    args = parser.parse_args()

    if args.file:
        json_path = Path(args.file)
    else:
        files = sorted(
            RESULTS_DIR.glob("scenario_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not files:
            print("scenario 결과 파일을 찾을 수 없습니다.")
            return
        json_path = files[0]
        print(f"파일 자동 선택: {json_path.name}")

    with json_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

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

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results:
            writer.writerow(parse_entry(entry))

    parse_fail = sum(1 for entry in results if not entry.get("scenario_parsed"))
    print("\n메타 정보:")
    print(f"  모델: {meta.get('model')}")
    print(f"  scenario_temperature: {meta.get('scenario_temperature')}")
    print(f"  장소: {meta.get('location')}")
    print(f"  레벨: {meta.get('level')}")
    print(f"  runs: {meta.get('runs')}")
    print(f"  파싱 실패: {parse_fail}건")
    print(f"\nCSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    main()
