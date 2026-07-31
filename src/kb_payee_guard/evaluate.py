"""A/B/C 베이스라인 비교 — AI 필연성의 수치 증명.

## 무엇을 재는가

단순 필드 정확도는 이 문제에 맞지 않는다. `notice_clause` 문자열이 조금 달라도
판정이 같으면 실질적으로 같은 추출이고, 반대로 `amendment_clause_requires_written`
불리언 하나가 뒤집히면 등급이 PASS에서 BLOCK_PENDING으로 간다.

그래서 두 층위로 잰다:

1. **허용 경로 집합 정확도** (추출 층위)
   추출 결과로부터 "이 계약서에서 어떤 경로의 계좌 지시가 고위험이 아닌가"를 계산하면
   `InstructionSource` 부분집합이 나온다. 이것이 S16이 실제로 쓰는 유일한 투영이다.
   집합 비교이므로 accuracy가 아니라 **exact-match + Jaccard**로 잰다.

2. **판정 일치율** (end-to-end)
   같은 송금 신청에 대해 gold facts로 낸 등급과 추출 facts로 낸 등급이 같은가.
   이것이 사용자에게 실제로 도달하는 차이다.

## 왜 이 설계가 AI 필연성을 증명하는가

Baseline A(정규식)는 조항을 **찾을** 수는 있다. 그러나 조항이 **허용하는 경로**를
판정하지 못한다 — 'in writing'이라는 문자열은 요구조건일 때도 선택지일 때도 나온다.
1번 지표는 정확히 그 차이에서 갈린다. A가 여기서 C를 이기면 AI는 불필요하고,
그때는 후보를 폐기하는 것이 옳다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    AccountInstruction,
    ContractFacts,
    InstructionSource,
    RemittanceRequest,
    Severity,
    Verdict,
)
from . import rules, signals

# 계좌 지시가 올 수 있는 경로 전체
ALL_SOURCES: tuple[InstructionSource, ...] = tuple(InstructionSource)


def allowed_paths(facts: ContractFacts) -> frozenset[InstructionSource]:
    """이 계약서 하에서 '고위험이 아닌' 계좌 지시 경로의 집합.

    S16이 계약서로부터 쓰는 것은 이 투영이 전부다. 추출기의 품질을
    이 집합의 정확도로 재는 이유 — 원문을 얼마나 예쁘게 뽑았는지가 아니라,
    판정을 바꾸는 정보를 뽑았는지가 문제다.

    EMAIL은 발신 주소에 따라 갈리므로, 계약서가 아는 주소에서 온 경우로 평가한다
    (계약서가 주소를 모르면 어떤 주소든 마찬가지다).
    """
    known = facts.notice_channels or facts.registered_contact
    probe_addr = known[0] if known else "unknown@example.invalid"
    out = []
    for src in ALL_SOURCES:
        detail = probe_addr if src is InstructionSource.EMAIL else None
        hit = signals.check_s16(facts, AccountInstruction(src, detail))
        if hit.severity is not Severity.HIGH:
            out.append(src)
    return frozenset(out)


@dataclass
class CaseResult:
    case_id: str
    extractor: str
    path_exact: bool
    path_jaccard: float
    verdict_match: bool
    gold_verdict: Verdict
    got_verdict: Verdict


@dataclass
class Report:
    extractor: str
    n: int = 0
    path_exact: int = 0
    jaccard_sum: float = 0.0
    verdict_match: int = 0
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def path_exact_rate(self) -> float:
        return self.path_exact / self.n if self.n else 0.0

    @property
    def path_jaccard(self) -> float:
        return self.jaccard_sum / self.n if self.n else 0.0

    @property
    def verdict_agreement(self) -> float:
        return self.verdict_match / self.n if self.n else 0.0

    def as_row(self) -> str:
        return (f"{self.extractor:<12} n={self.n:<4} "
                f"경로집합 정확일치={self.path_exact_rate:6.1%}  "
                f"Jaccard={self.path_jaccard:6.1%}  "
                f"판정일치={self.verdict_agreement:6.1%}")


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def score(
    extractor_name: str,
    pairs: list[tuple[str, ContractFacts, ContractFacts, list[RemittanceRequest]]],
) -> Report:
    """pairs: (case_id, gold_facts, predicted_facts, 평가에 쓸 송금 신청들)

    송금 신청은 케이스마다 여러 개일 수 있다 — 같은 계약서에 대해 여러 경로의
    지시를 넣어봐야 추출 오류가 판정에 미치는 영향이 드러난다.
    """
    rep = Report(extractor_name)
    for case_id, gold, pred, reqs in pairs:
        g_paths, p_paths = allowed_paths(gold), allowed_paths(pred)
        exact = g_paths == p_paths
        jac = _jaccard(g_paths, p_paths)

        matches = 0
        for req in reqs:
            gv = rules.evaluate(gold, req).verdict
            pv = rules.evaluate(pred, req).verdict
            matches += (gv == pv)
        vmatch = matches == len(reqs) if reqs else True

        rep.n += 1
        rep.path_exact += exact
        rep.jaccard_sum += jac
        rep.verdict_match += vmatch
        rep.cases.append(CaseResult(
            case_id, extractor_name, exact, jac, vmatch,
            rules.evaluate(gold, reqs[0]).verdict if reqs else Verdict.UNKNOWN,
            rules.evaluate(pred, reqs[0]).verdict if reqs else Verdict.UNKNOWN,
        ))
    return rep


def clause_presence(facts_list: list[ContractFacts]) -> dict[str, float]:
    """R-7 측정 — 계약서에 절차 조항이 실제로 얼마나 있는가.

    🔴 이 숫자가 S16의 생사를 정한다. 낮으면 §Notices·§Amendment 경로가 소수이고,
       S16-b fallback(계약서 기재 연락처 준거)이 선택이 아니라 주 경로가 된다.
       한 번도 세어본 적이 없어 R-7이 '최우선 미확인'으로 남아 있었다.
    """
    n = len(facts_list) or 1
    return {
        "n": len(facts_list),
        "notice_clause": sum(f.notice_clause is not None for f in facts_list) / n,
        "notice_channels": sum(bool(f.notice_channels) for f in facts_list) / n,
        "amendment_clause": sum(f.amendment_clause is not None for f in facts_list) / n,
        "requires_written": sum(f.amendment_clause_requires_written for f in facts_list) / n,
        "registered_contact": sum(bool(f.registered_contact) for f in facts_list) / n,
        "payment_terms": sum(f.payment_terms is not None for f in facts_list) / n,
    }
