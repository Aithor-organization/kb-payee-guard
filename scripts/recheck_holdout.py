#!/usr/bin/env python3.12
"""커밋된 holdout 결과를 **API 키 없이** 다시 집계한다.

## 왜 필요한가 (2026-08-03, cross-model 리뷰 지적)

README 가 `run_e2e.py --corpus holdout --extract A` 를 92.9% 의 재현 경로처럼 적어 두었는데,
**그 명령은 정규식 경로라 22.4% 를 낸다.** 92.9% 는 LLM 경로(`--extract C`) 결과이고 그것을
재현하려면 OpenAI 키와 10분, 약 $0.17 이 든다 — 심사자가 확인할 수 없는 숫자였다.

그래서 **커밋된 원자료**(`data/contracts/_e2e_*.json` 의 `rows`)를 읽어 그대로 다시 세는 경로를 둔다.
키도 네트워크도 필요 없다.

⚠️ **이 스크립트가 내는 것은 README 성능표의 차단율·오탐률뿐이다.** 추출 정확도(90.0%/91.7%,
`docs/05`)나 조항 보유율(`docs/03`)은 별도 측정이라 여기서 나오지 않는다.

    python3.12 scripts/recheck_holdout.py

## 대상/비대상 판정은 어디서 오는가

`_corpus_manifest.json` 이다. 이전에는 `run_e2e.py` 안에 `OFF_TARGET={"kr"}` 로 **접두사를
하드코딩**했는데, 그러면 접두사 하나를 추가하는 것만으로 숫자를 올릴 수 있다.
매니페스트는 **문서별로 사유를 적게** 강제하므로 그 조작이 눈에 보인다.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "data" / "contracts"
MANIFEST = CONTRACTS / "_corpus_manifest.json"

STOPPED = {"HOLD", "BLOCK_PENDING"}       # 위험 판정 → 승인 요구
KNOWN_GAP = "attack_forged_amendment"     # 설계상 알려진 미탐


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        sys.exit(f"🔴 {MANIFEST} 가 없습니다.")
    return {e["file"]: e for e in json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"]}


def tally(rows: list[dict], keep) -> dict[str, int]:
    t = defaultdict(int)
    for r in rows:
        if not keep(r["file"]):
            continue
        stopped = r["verdict"] in STOPPED
        unknown = r["verdict"] == "UNKNOWN"
        if r["expect_block"]:
            t["atk_total"] += 1
            t["atk_stopped"] += stopped
            t["atk_unknown"] += unknown
            if r["kind"] != KNOWN_GAP:
                t["ex_total"] += 1
                t["ex_stopped"] += stopped
        else:
            t["norm_total"] += 1
            t["norm_stopped"] += stopped
            t["norm_unknown"] += unknown
    return t


def line(label: str, t: dict[str, int], n_docs: int) -> str:
    a, e, n = t["atk_total"] or 1, t["ex_total"] or 1, t["norm_total"] or 1
    return (f"  {label:<26}{n_docs:>4}건   "
            f"전체공격 {t['atk_stopped']:>3}/{a:<4}={t['atk_stopped']/a:>6.1%}   "
            f"위조제외 {t['ex_stopped']:>3}/{e:<4}={t['ex_stopped']/e:>6.1%}   "
            f"정상 자동통과 {(n - t['norm_stopped'] - t['norm_unknown'])/n:>6.1%}")


def main() -> None:
    man = load_manifest()
    off = {f for f, e in man.items() if e["off_target"]}

    print("커밋된 원자료 재집계 — API 키 불필요\n")
    for src, label in (("_e2e_result_gold.json", "gold · 완전추출 상한"),
                       ("_e2e_result_C.json", "gold · LLM"),
                       ("_e2e_result_A.json", "gold · 정규식"),
                       ("_e2e_holdout_C.json", "holdout · LLM"),
                       ("_e2e_holdout_A.json", "holdout · 정규식")):
        p = CONTRACTS / src
        if not p.exists():
            print(f"  ⚠️  {src} 없음 — 건너뜀")
            continue
        rows = json.loads(p.read_text(encoding="utf-8"))["rows"]
        docs = {r["file"] for r in rows}
        print(f"── {label}  ({src})")
        print(line("전체", tally(rows, lambda f: True), len(docs)))
        if docs & off:
            keep = lambda f: f not in off        # noqa: E731
            print(line("└ 대상 문서군만", tally(rows, keep), len(docs - off)))
            print(line("└ ⚠️ 비대상만", tally(rows, lambda f: f in off), len(docs & off)))
        print()

    reasons = defaultdict(int)
    for f in off:
        reasons[man[f]["reason"]] += 1
    print(f"비대상 판정 {len(off)}건 (사유별):")
    for r, n in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"   {n:>3}건  {r}")
    print(f"\n🔴 이 수치는 '독립 정답 라벨 대비 정확도'가 아니다 — 시나리오가 추출 결과로")
    print(f"   생성되므로(scenarios.build), '추출이 비지 않았을 때 규칙이 설계대로 발화하는가'를 센다.")


if __name__ == "__main__":
    main()
