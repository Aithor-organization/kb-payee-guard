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
  않는다) 비교가 성립한다. 결과는 `_e2e_holdout_{A,C}.json` 에 추출기별로 따로 쓴다.

  ⚠️ `--corpus holdout` 은 `--extract gold` 와 함께 쓸 수 없다.
     gold facts 는 라벨이 있는 30건에만 존재하기 때문이다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_payee_guard import rules, scenarios  # noqa: E402
from kb_payee_guard.extract import RegexExtractor  # noqa: E402
from kb_payee_guard.models import ContractFacts, PaymentTerms, Verdict  # noqa: E402

GOLD = ROOT / "data" / "contracts" / "_gold.json"
# 🔴 단일 출력 상수(_e2e_result.json)는 2026-08-03 에 제거했다 — 경로는 result_out() 이
#    (코퍼스 × 추출기)별로 만든다. 되살리면 2026-08-02 의 덮어쓰기 사고가 재발한다.
CONTRACTS = ROOT / "data" / "contracts"


def result_out(corpus: str, extractor: str) -> Path:
    """🔴 **결과 파일은 (코퍼스 × 추출기)마다 나눈다** (2026-08-03).

    이전에는 gold 코퍼스의 세 추출 경로(gold-facts / A / C)가 **같은 `_e2e_result.json` 하나를
    공유**했다. 그래서 나중에 돌린 것이 앞의 것을 조용히 덮어썼고, 실제로 이 세션에서
    `--extract A` 를 한 번 돌리자 README 가 인용하던 **gold·LLM 원자료가 사라졌다.**
    (holdout 은 2026-08-02 에 같은 이유로 이미 분리했는데 gold 를 빠뜨렸다.)

    커밋된 원자료로 표를 재현할 수 있어야 하므로 경로를 완전히 분리한다.
    """
    stem = "_e2e_holdout" if corpus == "holdout" else "_e2e_result"
    return CONTRACTS / f"{stem}_{extractor}.json"


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


EXTRACT_RETRIES = 3
EXTRACT_BACKOFF = (2.0, 8.0)


def extract_resilient(extractor, text: str, fn: str):
    """추출 1건이 실패해도 **전체 실행을 죽이지 않는다**.

    🔴 2026-08-02 실사건: holdout 232건 평가가 130번째(`sec-047.txt`)에서
       `TimeoutError` 로 두 번 연속 중단됐다. 그때까지의 129건 결과가 통째로 사라졌다.

       처음엔 `_provider_fallback._default_transport` 에 재시도를 넣었는데
       **효과가 없었다** — `llm_extract` 가 sibling repo 를 `sys.path` 에 넣어
       내 머신에서는 프레임워크 provider 가 쓰이기 때문이다(심사자 환경에서는 fallback).
       그래서 **provider 아래가 아니라 위**에 둔다. 어느 구현을 쓰든 동일하게 걸린다.

       재시도해도 안 되면 그 건만 포기하고 진행한다 — 빈 `ContractFacts` 는
       R1 이 `UNKNOWN` 으로 처리하므로 **통과가 아니라 보류**다 (INV-5 유지).
    """
    for attempt in range(EXTRACT_RETRIES):
        try:
            return extractor.extract(text)
        except Exception as exc:                     # noqa: BLE001 — 어떤 실패든 전체를 죽이면 안 된다
            tag = f"{type(exc).__name__}: {str(exc)[:80]}"
            if attempt < EXTRACT_RETRIES - 1:
                print(f"      ↻ {fn} 재시도 {attempt + 1}/{EXTRACT_RETRIES - 1} ({tag})", flush=True)
                time.sleep(EXTRACT_BACKOFF[attempt])
            else:
                print(f"      ⚠️  {fn} 추출 포기 → UNKNOWN 으로 계산 ({tag})", flush=True)
    return None


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

    extract_failed: list[str] = []
    for i, fn in enumerate(files, 1):
        text = (ROOT / "data" / "contracts" / fn).read_text(encoding="utf-8", errors="replace")
        if extractor is None:
            facts = gold_facts(fn, gold[fn]["kind"], text)
        else:
            facts = extract_resilient(extractor, text, fn)
            if facts is None:
                # 🔴 한 건이 죽어도 전체를 버리지 않는다. 빈 사실 = 추출 실패 =
                #    R1 이 UNKNOWN 을 내므로 **통과가 아니라 보류**로 계산된다 (INV-5).
                extract_failed.append(fn)
                facts = ContractFacts()

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

    # 🔴 3-상태 집계 (2026-08-03 추가 — cross-model 리뷰가 잡은 결함)
    #
    #   `BLOCKING` 은 {HOLD, BLOCK_PENDING} 이라 **UNKNOWN 을 뺀다.** 그런데 실제 게이트의
    #   `_NEEDS_APPROVAL` 은 UNKNOWN 을 **포함**한다 (gate.py). 즉 지표와 제품이 어긋나 있었다:
    #
    #     · 정상 UNKNOWN → "오차단 아님" 으로 세어 **오탐률을 실제보다 낮게** 보이게 했다.
    #       하드 차단은 아니지만 사람 승인 없이는 못 지나가므로 **현장 마찰은 존재**한다.
    #     · 공격 UNKNOWN → "차단 아님" 으로 세어 **탐지율을 실제보다 낮게** 계상했다.
    #
    #   어느 쪽으로 합치든 한쪽이 왜곡되므로 **합치지 않고 세 상태를 그대로 보고**한다.
    #   INV-5("판정 불가를 통과로 처리하지 않는다")를 지표에서도 지키는 유일한 방법이다.
    def _tri(expect_block: bool) -> dict[str, int]:
        sel = [r for r in rows if r["expect_block"] is expect_block]
        stop = sum(1 for r in sel if r["verdict"] in {"HOLD", "BLOCK_PENDING"})
        unk = sum(1 for r in sel if r["verdict"] == "UNKNOWN")
        return {"stopped": stop, "unknown": unk, "auto_passed": len(sel) - stop - unk,
                "total": len(sel)}

    tri = {"normal": _tri(False), "attack": _tri(True)}

    # 🔴 코퍼스별 분해 (2026-08-03 추가)
    #
    #   holdout 232건은 균질하지 않다. `kr-*` 49건은 국가법령정보센터의 **공식 표준약관·
    #   일반조건·서식**이라 **체결 당사자가 채워져 있지 않다**(법인격 표기 0.0% · L/C 2.0%).
    #   업종은 공사·물품·용역이 다수지만 디지털콘텐츠·이러닝·화물운송·외자계약도 섞여 있어
    #   "국내 조달" 로 뭉뚱그릴 수 없다.
    #
    #   ⚠️ **원인은 확정하지 못했다.** ①송금 계약이 아니라서 ②한국어 추출이 어려워서 —
    #   국문 표본이 전부 서식이라 둘을 분리할 데이터가 없다 (docs/03 §3-ter-1).
    #   그래서 여기서 하는 일은 "국문을 빼는" 것이 아니라 **대상/비대상을 나눠 둘 다 보고**
    #   하는 것이다. 낮은 쪽을 숨기지 않기 위해서다.
    # 🔴 접두사 하드코딩을 버리고 **문서별 매니페스트**를 읽는다 (2026-08-03).
    #    `OFF_TARGET={"kr"}` 는 접두사 하나만 추가하면 숫자가 올라가는 구조라
    #    cross-model 리뷰가 "조작 가능"으로 지적했다. 매니페스트는 문서마다 사유를
    #    적게 강제하므로 같은 조작이 눈에 보인다. 판정 기준은 국문 여부가 아니라
    #    **"체결 당사자가 채워졌는가"** 이고 전 코퍼스에 동일 적용한다.
    _man = CONTRACTS / "_corpus_manifest.json"
    _off_files: set[str] = set()
    if _man.exists():
        _off_files = {d["file"] for d in json.loads(_man.read_text(encoding="utf-8"))["documents"]
                      if d["off_target"]}
    # 🔴 접두사로 축약하지 않는다 (2026-08-03). 축약하면 한 접두사 안에 대상·비대상이
    #    섞였을 때 코퍼스 전체가 통째로 빠진다 — 하드코딩 구조가 이름만 바뀌어 남는 셈이다.
    #    판정도 합산도 **파일 단위**로 한다.
    by_corpus: dict[str, dict[str, int]] = {}
    for r in rows:
        c = r["file"].split("-")[0]
        d = by_corpus.setdefault(c, {"atk_blocked": 0, "atk_total": 0, "atk_excl_blocked": 0,
                                     "atk_excl_total": 0, "norm_total": 0, "norm_unknown": 0})
        blocked = r["verdict"] in {"HOLD", "BLOCK_PENDING"}
        if r["expect_block"]:
            d["atk_total"] += 1; d["atk_blocked"] += blocked
            if r["kind"] != "attack_forged_amendment":
                d["atk_excl_total"] += 1; d["atk_excl_blocked"] += blocked
        else:
            d["norm_total"] += 1; d["norm_unknown"] += r["verdict"] == "UNKNOWN"
    result = {"extract_failed": extract_failed, "corpus": args.corpus, "extractor": args.extract, "n_contracts": len(files),
              "detection_rate": det, "false_positive_rate": fp, "tri_state": tri,
              "by_corpus": by_corpus, "off_target_files": sorted(_off_files), **stats, "rows": rows}
    out_path = result_out(args.corpus, args.extract)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    per = len(rows) // (len(files) or 1)
    print(f"\n코퍼스: {args.corpus}   추출 경로: {args.extract}   (계약서 {len(files)}건 × 시나리오 {per} = {len(rows)}건)")
    print("-" * 62)
    print(f"  🎯 BEC 탐지율      {det:6.1%}   ({stats['attack_blocked']}/{stats['attack_total']} 차단)")
    print(f"  🟢 정상거래 오탐률  {fp:6.1%}   ({stats['normal_total'] - stats['normal_passed']}"
          f"/{stats['normal_total']} 잘못 차단)")
    print(f"     └ 알려진 사각지대(위조 수정합의서) 제외 시   {det_excl:6.1%}"
          f"   — 미탐 {len(known_gap) - sum(r['ok'] for r in known_gap)}건은 설계상 예견된 것")
    n, a = tri["normal"], tri["attack"]
    print()
    print(f"  ── 3-상태 (게이트 실제 동작 기준: UNKNOWN 도 사람 승인 필요) ──")
    print(f"     정상 {n['total']:>4}건   자동통과 {n['auto_passed']:>4} ({n['auto_passed']/(n['total'] or 1):5.1%})"
          f" · 사람승인 {n['unknown']:>4} ({n['unknown']/(n['total'] or 1):5.1%})"
          f" · 하드차단 {n['stopped']:>4} ({n['stopped']/(n['total'] or 1):5.1%})")
    print(f"     공격 {a['total']:>4}건   차단     {a['stopped']:>4} ({a['stopped']/(a['total'] or 1):5.1%})"
          f" · 보류     {a['unknown']:>4} ({a['unknown']/(a['total'] or 1):5.1%})"
          f" · 자동통과 {a['auto_passed']:>4} ({a['auto_passed']/(a['total'] or 1):5.1%})")

    if len(by_corpus) > 1:
        print()
        print("  ── 코퍼스별 (⚠️ = 송금 계약이 아닌 문서군) ──")
        # 접두사별 표시는 유지하되, ⚠️ 표식은 "그 접두사가 전부 비대상인가" 로 판단한다
        prefix_all_off = {c: all(r["file"] in _off_files
                                 for r in rows if r["file"].split("-")[0] == c)
                          for c in by_corpus}
        prefix_any_off = {c: any(r["file"] in _off_files
                                 for r in rows if r["file"].split("-")[0] == c)
                          for c in by_corpus}
        for c, d in sorted(by_corpus.items()):
            mark = "⚠️" if prefix_all_off[c] else ("◐ " if prefix_any_off[c] else "  ")
            ex = d["atk_excl_blocked"] / (d["atk_excl_total"] or 1)
            unk = d["norm_unknown"] / (d["norm_total"] or 1)
            print(f"   {mark} {c:<6} 위조제외 차단 {d['atk_excl_blocked']:>4}/{d['atk_excl_total']:<4} = {ex:>6.1%}"
                  f"   정상 UNKNOWN {unk:>6.1%}")
        # 합산은 **파일 단위** — 접두사가 아니라 매니페스트가 정본이다
        tb = sum(1 for r in rows if r["expect_block"] and r["kind"] != "attack_forged_amendment"
                 and r["file"] not in _off_files and r["verdict"] in {"HOLD", "BLOCK_PENDING"})
        tt = sum(1 for r in rows if r["expect_block"] and r["kind"] != "attack_forged_amendment"
                 and r["file"] not in _off_files)
        if tt:
            print(f"      {'대상 문서군만':<12} {tb:>4}/{tt:<4} = {tb/tt:>6.1%}"
                  f"   (매니페스트 기준 · 비대상 {len(_off_files)}건 제외)")

    by_kind: dict[str, list[bool]] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r["ok"])
    print(f"\n  {'시나리오':<26}{'정답률':>8}")
    for k, v in by_kind.items():
        print(f"  {k:<26}{sum(v)/len(v):>7.1%}")
    if extract_failed:
        print(f"\n⚠️  추출 실패 {len(extract_failed)}건 (UNKNOWN 처리): "
              f"{', '.join(extract_failed[:5])}"
              f"{' 외 ' + str(len(extract_failed) - 5) + '건' if len(extract_failed) > 5 else ''}")
    print(f"\n결과: {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
