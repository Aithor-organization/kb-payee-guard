"""L4 규칙 테이블 판정 (결정론) + 도달성 검사.

기술명세서 §4.4의 코드화.

🔴 판정에 튜닝할 계수가 없다. 규칙의 조건이 곧 사용자에게 보이는 문장이고,
   조정할 가중치도 임계값도 존재하지 않는다. 대신 도달성 전수 검사(T15)로
   '모든 규칙은 발화해야 한다'를 강제한다 — 조용한 침묵은 오탐보다 위험하다.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .models import (
    AccountInstruction,
    ContractFacts,
    RemittanceRequest,
    Severity,
    SignalHit,
    Verdict,
)
from . import signals as sig


@dataclass
class SignalSet:
    """규칙 테이블이 읽는 신호 상태. 규칙은 이 구조체만 본다."""

    extraction_failed: bool = False
    S16_severity: Severity = Severity.NONE
    S9: bool = False
    S10_severity: Severity = Severity.NONE
    S11: bool = False
    S12: bool = False
    S1: bool = False
    S5: bool = False
    M1: bool = False
    M2: bool = False
    M6: bool = False   # LLM 신호 (긴급성 압박) — 미주입 시 False
    M8: bool = False   # LLM 신호 (통지조항 위반 정황) — 미주입 시 False

    hits: list[SignalHit] = field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    verdict: Verdict
    why: str


# 평가 순서: R1 → R2 → … → R11 → R0 (first-match wins)
_RULES: list[tuple[Rule, object]] = [
    (Rule("R1", Verdict.UNKNOWN, "계약서 부재 또는 추출 실패"),
     lambda s: s.extraction_failed),
    (Rule("R2", Verdict.BLOCK_PENDING, "계좌 지시가 계약 절차 조항을 위반한 경로로 옴 (최빈 BEC)"),
     lambda s: s.S16_severity is Severity.HIGH),
    (Rule("R3", Verdict.BLOCK_PENDING, "계약 상대방 소재국과 계좌 개설국 불일치"),
     lambda s: s.S9),
    (Rule("R4", Verdict.BLOCK_PENDING, "결제조건이 위험한 방향으로 전환됨"),
     lambda s: s.S10_severity is Severity.HIGH),
    (Rule("R5", Verdict.BLOCK_PENDING, "계약 수익자명과 수취인명 불일치"),
     lambda s: s.S11),
    (Rule("R6", Verdict.BLOCK_PENDING, "발신 도메인이 계약서 기재 도메인과 유사하지만 다름"),
     lambda s: s.M1),
    (Rule("R7", Verdict.HOLD, "계좌 지시 근거가 약함 (절차 조항 부재 또는 인보이스 단독)"),
     lambda s: s.S16_severity is Severity.MEDIUM),
    (Rule("R8", Verdict.HOLD, "결제조건 변경 또는 계약 금액 초과"),
     lambda s: s.S10_severity is Severity.MEDIUM or s.S12),
    (Rule("R9", Verdict.HOLD, "신규 계좌 + 보강 신호"),
     lambda s: s.S1 and (s.M2 or s.M6 or s.M8)),
    (Rule("R10", Verdict.HOLD, "신규 계좌 (보강 신호 없음)"),
     lambda s: s.S1),
    (Rule("R11", Verdict.NOTICE, "계약서와 일치하나 계좌 개설국이 고위험 관할"),
     lambda s: s.S5),
    (Rule("R0", Verdict.PASS, "계약서와 송금 정보가 일치"),
     lambda s: True),
]

RULE_IDS = [r.rule_id for r, _ in _RULES]


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    rule_id: str
    why: str
    hits: tuple[SignalHit, ...]

    def reasons(self) -> list[str]:
        """사용자에게 보이는 근거 문장. 판정과 설명이 같은 곳에서 나온다."""
        return [h.detail for h in self.hits if h.severity is not Severity.NONE]


def decide(s: SignalSet) -> Decision:
    for rule, cond in _RULES:
        if cond(s):
            return Decision(rule.verdict, rule.rule_id, rule.why, tuple(s.hits))
    raise AssertionError("R0가 항상 매치해야 한다 — 여기 오면 규칙 테이블이 깨진 것")


def evaluate(facts: ContractFacts, req: RemittanceRequest,
             *, m6: bool = False, m8: bool = False) -> Decision:
    """L1 추출 결과 + 송금 신청 → 등급.

    m6/m8은 LLM 보조 신호다. 주입되지 않으면 False — 🔴 이것이 옳다.
    LLM이 판정 축에 없다는 것이 INV-6이고, 보조 신호가 없다고 게이트가 꺼지면 안 된다.
    """
    if not req.has_contract or facts.is_empty():
        return Decision(Verdict.UNKNOWN, "R1", "계약서 부재 또는 추출 실패", ())

    hits: list[SignalHit] = []
    s = SignalSet(M6=m6, M8=m8)

    s16 = sig.check_s16(facts, req.account_instruction)
    s.S16_severity = s16.severity
    hits.append(s16)

    for check, setter in (
        (sig.check_s9(facts, req), "S9"),
        (sig.check_s10(facts, req), "S10"),
        (sig.check_s11(facts, req), "S11"),
        (sig.check_s12(facts, req), "S12"),
        (sig.check_s5(facts, req), "S5"),
        (sig.check_m1(facts, req), "M1"),
        (sig.check_m2(req), "M2"),
        (sig.check_s1(req), "S1"),
    ):
        if check is None:
            continue
        hits.append(check)
        if setter == "S10":
            s.S10_severity = check.severity
        else:
            setattr(s, setter, True)

    s.hits = hits
    return decide(s)


# ── T15 도달성 전수 검사 ───────────────────────────────────────────────────────

_SEVERITIES = (Severity.NONE, Severity.MEDIUM, Severity.HIGH)


def _domains(pinned: dict[str, object] | None = None) -> dict[str, tuple]:
    """SignalSet의 각 필드가 취할 수 있는 값. 필드명으로 도출하므로
    필드가 추가돼도 자동으로 커버된다.

    🔴 위치 인자(`SignalSet(*combo)`)로 만들면 안 된다. 필드를 하나 추가하는 순간
       튜플이 한 칸씩 밀려 엉뚱한 필드를 흔들고, 검사는 통과하는데 실제로는
       아무것도 검사하지 않는 상태가 된다 — 가드가 조용히 실명한다.
       (본 구현 중 실제로 발생시켜 확인함)
    """
    out: dict[str, tuple] = {}
    for name, f in SignalSet.__dataclass_fields__.items():
        if name == "hits":
            continue
        out[name] = _SEVERITIES if "Severity" in str(f.type) else (False, True)
    for k, v in (pinned or {}).items():
        out[k] = (v,)
    return out


def unreachable_rules(pinned: dict[str, object] | None = None) -> list[str]:
    """모든 규칙이 어떤 입력 조합에서든 실제로 발화하는지 전수 확인한다.

    dead rule은 조용히 죽는다 — v3.0에서 R7·R8이 입력 스키마에 없는 필드를
    참조해 영영 발화하지 않았고, 그 사이 최빈 BEC에 전 규칙이 침묵했다.
    R11도 정의되지 않은 S5를 참조하고 있었다. 이 검사가 그 회귀를 막는다.

    `pinned`로 특정 신호를 고정하면 "그 신호가 죽으면 어떤 규칙이 같이 죽는가"를
    확인할 수 있다 — 이 검사 자체가 작동하는지 검증하는 용도다.
    """
    domains = _domains(pinned)
    names = list(domains)
    fired: set[str] = set()
    for combo in itertools.product(*(domains[n] for n in names)):
        fired.add(decide(SignalSet(**dict(zip(names, combo)))).rule_id)  # type: ignore[arg-type]
    return [rid for rid in RULE_IDS if rid not in fired]
