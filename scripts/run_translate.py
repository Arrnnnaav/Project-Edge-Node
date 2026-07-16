import json
import sys
from pathlib import Path

# add project root to sys.path so `app` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schema import LableMeta
from app.translate import to_text

DATA_PATH = Path("data/synthetic_logs.json")  # <-- update to your actual path

def main():
    rows = json.loads(DATA_PATH.read_text())
    print(f"Loaded {len(rows)} rows from {DATA_PATH}\n")

    ok, failed, gap_leaks = 0, [], []

    for i, row in enumerate(rows):
        try:
            log = LableMeta(**row)
        except Exception as e:
            failed.append((i, row, str(e)))
            continue

        try:
            text = to_text(log)
        except Exception as e:
            failed.append((i, row, f"to_text crashed: {e}"))
            continue

        # regression guard for the gap-phrase bug
        if log.total_meetings <= 1 and "gap" in text:
            gap_leaks.append((i, text))
            continue

        ok += 1
        if i < 5:
            print(f"[{i}] label={log.label}\n{text}\n")

    print(f"\n{ok}/{len(rows)} rows translated cleanly.")

    if gap_leaks:
        print(f"\n{len(gap_leaks)} rows LEAKED 'gap' phrase for total_meetings<=1:")
        for i, text in gap_leaks[:10]:
            print(f"  row {i}: {text}")

    if failed:
        print(f"\n{len(failed)} rows FAILED validation or translation:")
        for i, row, err in failed[:20]:
            print(f"  row {i}: {err}")
            print(f"    data: {row}")

    if failed or gap_leaks:
        sys.exit(1)
    else:
        print("\nAll rows passed. ✅")


if __name__ == "__main__":
    main()