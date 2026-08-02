#!/usr/bin/env python3.12
"""End-to-end 평가 — 탐지율과 오탐률을 같은 파이프라인에서 잰다.

사용법:
  python3.12 scripts/run_e2e.py             # gold facts 기준 (상한 성능)
  python3.12 scripts/run_e2e.py --extract C # C 추출기를 실제로 거친 성능 (OpenAI 호출)
  python3.12 scripts/run_e2e.py --extract A # 정규식 추출기 경유

두 모드의 차이가 곧 **추출 품질이 최종 판정에 미치는 영향**이다.

🎯 holdout 평가 (2026-08-02 신설):
  python3.12 scripts/run_e2e.py --corpus holdout --extract A

  기본 `--corpus gold` 는 규칙을 고치는 데 **사용한** 30건이라 일반화 성능이 아니다.
  `holdout` 은 gold 에 없는 계약서 전부 — 규칙 튜닝에 한 번도 쓰이지 않았다.
  같은 시나리오 5종을 그대로 합성하므로(`scenarios.build` 는 gold 라벨에 의존하지
  않는다) 비교가 성립한다. 결과는 `_e2e_holdout.json` 에 따로 쓴다.

  ⚠️ `--corpus holdout` 은 `--extract gold` 와 함께 쓸 수 없다.
     gold facts 는 라벨이 있는 30건에만 존재하기 때문이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_payee_guard import rules, scenarios  # noqa: E402
from kb_payee_guard.extract import RegexExtractor  # noqa: E402
from kb_payee_guard.models import ContractFacts, PaymentTerms, Verdict  # noqa: E402

GOLD = ROOT / "data" / "contracts" / "_gold.json"
OUT = ROOT / "data" / "contracts" / "_e2e_result.json"
OUT_HOLDOUT = ROOT / "data" / "contracts" / "_e2e_holdout.json"
CONTRACTS = ROOT / "data" / "contracts"


def gold_facts(fn: str, kind: str, text: str) -> ContractFacts:
    """gold 라벨 + 원문에서 뽑을 수 있는 사실로 '정답 추출 결과'를 구성한다.

    이 경로의 점수는 **추출이 완벽할 때의 상한**이다. 규칙 엔진 자체의 성능을 재기 위한 것.
    """
    a = RegexExtractor().extract(text)          # 이름·연락처·결제조건은 정규식으로도 잘 나온다
    return ContractFacts(
        counterparty_name=a.counterparty_name or "COUNTERPARTY",
        counterparty_country=a.counterparty_country or "DE",
        registered_contact=a.registered_contact or ["ops@counterparty.example"],
        notice_channels=a.notice_channels,
        payment_terms=a.payment_terms or PaymentTerms.TT,
        amendment_clause="(gold)" if kind == "written" else None,
        amendment_clause_requires_written=(kind == "written"),
        evidence_spans={"_source": "gold"},
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", choices=["gold", "A", "C"], default="gold")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--corpus", choices=["gold", "holdout"], default="gold",
                    help="gold=규칙 튜닝에 쓴 30건 / holdout=한 번도 안 쓴 나머지 전부")
    args = ap.parse_args()

    gold = json.loads(GOLD.read_text(encoding="utf-8"))["labels"]
    if args.corpus == "holdout":
        if args.extract == "gold":
            print("🔴 --corpus holdout 은 --extract gold 와 함께 쓸 수 없습니다.\n"
                  "   gold facts 는 라벨이 있는 30건에만 존재합니다. --extract A 또는 C 를 쓰세요.",
                  file=sys.stderr)
            return 2
        files = sorted(f.name for f in CONTRACTS.glob("*.txt") if f.name not in gold)
    else:
        files = sorted(gold)
    files = files[: args.limit or None]

    extractor = None
    if args.extract == "A":
        extractor = RegexExtractor()
    elif args.extract == "C":
        from kb_payee_guard.llm_extract import LLMExtractor
        extractor = LLMExtractor()

    rows, stats = [], {
        "attack_blocked": 0, "attack_total": 0,
        "normal_passed": 0, "normal_total": 0,
        "unknown": 0,
    }

    for i, fn in enumerate(files, 1):
        text = (ROOT / "data" / "contracts" / fn).read_text(encoding="utf-8", errors="replace")
        facts = (gold_facts(fn, gold[fn]["kind"], text) if extractor is None
                 else extractor.extract(text))

        for sc in scenarios.build(facts, fn):
            d = rules.evaluate(facts, sc.request)
            blocked = d.verdict in scenarios.BLOCKING
            correct = blocked == sc.expect_block
            if d.verdict is Verdict.UNKNOWN:
                stats["unknown"] += 1
            if sc.is_attack():
                stats["attack_total"] += 1
                stats["attack_blocked"] += blocked
            else:
                stats["normal_total"] += 1
                stats["normal_passed"] += not blocked
            rows.append({"file": fn, "kind": sc.kind, "verdict": d.verdict.value,
                         "rule": d.rule_id, "expect_block": sc.expect_block, "ok": correct})
        if args.extract == "C":
            print(f"  [{i}/{len(files)}] {fn}", flush=True)

    known_gap = [r for r in rows if r["kind"] == "attack_forged_amendment"]
    det = stats["attack_blocked"] / (stats["attack_total"] or 1)
    other_attacks = [r for r in rows if r["kind"].startswith("attack")
                     and r["kind"] != "attack_forged_amendment"]
    det_excl = sum(r["ok"] for r in other_attacks) / (len(other_attacks) or 1)
    fp = 1 - stats["normal_passed"] / (stats["normal_total"] or 1)
    result = {"corpus": args.corpus, "extractor": args.extract, "n_contracts": len(files),
              "detection_rate": det, "false_positive_rate": fp, **stats, "rows": rows}
    out_path = OUT_HOLDOUT if args.corpus == "holdout" else OUT
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    per = len(rows) // (len(files) or 1)
    print(f"\n코퍼스: {args.corpus}   추출 경로: {args.extract}   (계약서 {len(files)}건 × 시나리오 {per} = {len(rows)}건)")
    print("-" * 62)
    print(f"  🎯 BEC 탐지율      {det:6.1%}   ({stats['attack_blocked']}/{stats['attack_total']} 차단)")
    print(f"  🟢 정상거래 오탐률  {fp:6.1%}   ({stats['normal_total'] - stats['normal_passed']}"
          f"/{stats['normal_total']} 잘못 차단)")
    print(f"     └ 알려진 사각지대(위조 수정합의서) 제외 시   {det_excl:6.1%}"
          f"   — 미탐 {len(known_gap) - sum(r['ok'] for r in known_gap)}건은 설계상 예견된 것")
    if stats["unknown"]:
        print(f"  ⚠️  UNKNOWN         {stats['unknown']}건 (계약서 추출 실패 — 차단도 통과도 아님)")

    by_kind: dict[str, list[bool]] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r["ok"])
    print(f"\n  {'시나리오':<26}{'정답률':>8}")
    for k, v in by_kind.items():
        print(f"  {k:<26}{sum(v)/len(v):>7.1%}")
    print(f"\n결과: {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
