#!/usr/bin/env python3.12
"""A/B/C 베이스라인을 gold set에 돌려 비교표를 만든다.

사용법:
  python3.12 scripts/run_baselines.py            # A만 (무료·즉시)
  python3.12 scripts/run_baselines.py --with-c   # C 포함 (OpenAI 호출 발생)
  python3.12 scripts/run_baselines.py --with-c --limit 5

측정 대상은 `amendment_clause_requires_written` 하나다 — S16의 고위험/중위험을
가르는 유일한 비트이고, 그 비트가 최빈 BEC 차단 여부를 정한다.

결과는 data/contracts/_baseline_result.json 에 쓴다 (재현·인용용).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_payee_guard.extract import RegexExtractor  # noqa: E402
from kb_payee_guard.llm_extract import LLMExtractor  # noqa: E402

GOLD = ROOT / "data" / "contracts" / "_gold.json"
OUT = ROOT / "data" / "contracts" / "_baseline_result.json"


def confusion(pairs: list[tuple[bool, bool]]) -> dict[str, float | int]:
    """pairs: (gold, pred)"""
    tp = sum(1 for g, p in pairs if g and p)
    fp = sum(1 for g, p in pairs if not g and p)
    tn = sum(1 for g, p in pairs if not g and not p)
    fn = sum(1 for g, p in pairs if g and not p)
    n = len(pairs) or 1
    return {
        "n": len(pairs), "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "accuracy": (tp + tn) / n,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-c", action="store_true", help="C(LLM) 실행 — OpenAI 호출 발생")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="gpt-4o-mini")
    args = ap.parse_args()

    gold = json.loads(GOLD.read_text(encoding="utf-8"))["labels"]
    files = sorted(gold)
    if args.limit:
        files = files[: args.limit]

    a = RegexExtractor()
    c = LLMExtractor(model=args.model) if args.with_c else None

    rows: list[dict] = []
    a_pairs: list[tuple[bool, bool]] = []
    c_pairs: list[tuple[bool, bool]] = []

    for i, fn in enumerate(files, 1):
        text = (ROOT / "data" / "contracts" / fn).read_text(encoding="utf-8", errors="replace")
        g = gold[fn]["kind"] == "written"

        pa = a.extract(text).amendment_clause_requires_written
        a_pairs.append((g, pa))
        row = {"file": fn, "gold": g, "A": pa}

        if c:
            t0 = time.time()
            try:
                fc = c.extract(text)
                pc = fc.amendment_clause_requires_written
                row["C_error"] = None
            except Exception as exc:                       # noqa: BLE001 — 1건 실패가 전체를 멈추면 안 된다
                pc = False
                row["C_error"] = f"{type(exc).__name__}: {exc}"[:160]
            row["C"] = pc
            row["C_secs"] = round(time.time() - t0, 1)
            c_pairs.append((g, pc))
            mark = "✓" if pc == g else "✗"
            print(f"  [{i:2d}/{len(files)}] {fn:<16} gold={str(g):<5} "
                  f"A={str(pa):<5} C={str(pc):<5} {mark} {row['C_secs']}s", flush=True)

        rows.append(row)

    result = {
        "model": args.model if c else None,
        "n": len(files),
        "A-regex": confusion(a_pairs),
        "C-llm": confusion(c_pairs) if c else None,
        "rows": rows,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{'추출기':<10} {'n':>3} {'정확도':>8} {'precision':>10} {'recall':>8}   혼동행렬")
    print("-" * 66)
    for name, key in (("A-regex", "A-regex"), ("C-llm", "C-llm")):
        m = result[key]
        if not m:
            continue
        print(f"{name:<10} {m['n']:>3} {m['accuracy']:>7.1%} {m['precision']:>10.1%} "
              f"{m['recall']:>8.1%}   TP{m['TP']} FP{m['FP']} TN{m['TN']} FN{m['FN']}")

    if c:
        errs = [r for r in rows if r.get("C_error")]
        if errs:
            print(f"\n🔴 C 호출 실패 {len(errs)}건 (False로 계산됨 — recall 을 낮추는 방향):")
            for r in errs[:5]:
                print(f"   {r['file']}: {r['C_error']}")
    print(f"\n결과: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
