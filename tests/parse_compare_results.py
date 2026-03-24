"""compare 모드 결과 JSON → CSV 변환 스크립트.

구글 스프레드시트에 붙여넣기 위한 용도.

실행:
    python tests/parse_compare_results.py
    python tests/parse_compare_results.py --file tests/results/scenario_한강_compare_xxx.json
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import csv
import json


RESULTS_DIR = Path(__file__).parent / "results"


def parse_result(entry: dict, mode: str) -> dict:
    """node 또는 education_based 결과에서 비교용 필드를 추출한다."""
    parsed = entry.get("scenario_parsed") or {}
    ctx = entry.get("location_context") or ""
    is_fallback = "[solar-pro2:fallback]" in ctx if ctx else False

    return {
        f"{mode}_relationship_type": parsed.get("relationship_type", ""),
        f"{mode}_dialogue_function": ", ".join(parsed.get("dialogue_function", [])),
        f"{mode}_description": parsed.get("scenario_description", ""),
        f"{mode}_location_context_duration_s": entry.get("location_context_duration_s", ""),
        f"{mode}_scenario_duration_s": entry.get("scenario_duration_s", ""),
        f"{mode}_total_duration_s": entry.get("total_duration_s", ""),
        f"{mode}_parse_ok": "O" if parsed else "X",
        f"{mode}_fallback": "O" if is_fallback else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="결과 JSON 파일 경로 (없으면 최신 compare 파일 자동 선택)")
    args = parser.parse_args()

    if args.file:
        json_path = Path(args.file)
    else:
        files = sorted(RESULTS_DIR.glob("*compare*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            print("compare 결과 파일을 찾을 수 없습니다.")
            return
        json_path = files[0]
        print(f"파일 자동 선택: {json_path.name}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {})
    results = data.get("results", [])

    csv_path = json_path.with_suffix(".csv")

    model = meta.get("model", "")
    loc_ctx_temp = meta.get("location_context_temperature", "")
    scenario_temp = meta.get("scenario_temperature", "")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "run",
            "model",
            "location_context_temperature",
            "scenario_temperature",
            "node_relationship_type",
            "node_dialogue_function",
            "node_description",
            "node_location_context_duration_s",
            "node_scenario_duration_s",
            "node_total_duration_s",
            "node_parse_ok",
            "node_fallback",
            "eb_relationship_type",
            "eb_dialogue_function",
            "eb_description",
            "eb_location_context_duration_s",
            "eb_scenario_duration_s",
            "eb_total_duration_s",
            "eb_parse_ok",
            "eb_fallback",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for entry in results:
            row = {
                "run": entry.get("run", ""),
                "model": model,
                "location_context_temperature": loc_ctx_temp,
                "scenario_temperature": scenario_temp,
            }
            row.update(parse_result(entry.get("node", {}), "node"))
            row.update(parse_result(entry.get("education_based", {}), "eb"))
            writer.writerow(row)

    print(f"\n메타 정보:")
    print(f"  모델: {meta.get('model')}")
    print(f"  location_context_temperature: {meta.get('location_context_temperature')}")
    print(f"  scenario_temperature: {meta.get('scenario_temperature')}")
    print(f"  장소: {meta.get('location')}")
    print(f"  runs: {meta.get('runs')}")
    print(f"  node fallback 수: {sum(1 for r in results if '[solar-pro2:fallback]' in (r.get('node', {}).get('location_context') or ''))}")
    print(f"\nCSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    main()
