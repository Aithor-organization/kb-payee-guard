"""End-to-end 평가 시나리오 생성.

## 왜 필요한가

지금까지 측정한 것은 **추출 정확도**(A/C)뿐이다. 심사에서 반드시 나오는 두 질문에는
아직 답이 없었다:

  1. *"정상 거래를 얼마나 막습니까?"* — 오탐률. 게이트가 실용적인지를 정한다.
     이것이 조사노트가 **R-8**로 남겨둔 "한 번도 묻지 않았던 질문"이다.
  2. *"사기를 얼마나 잡습니까?"* — 탐지율. 제안서가 *"측정하지 않았다"* 고만 적어온 항목.

두 숫자는 같은 파이프라인에서 나온다. 입력만 다르다.

## 설계 원칙

🔴 **시나리오를 합성 계약서로 만들지 않는다.** 실물 계약서 30건에서 추출한 사실
(`ContractFacts`)을 그대로 쓰고, **송금 신청 쪽만** 바꾼다. 계약서가 진짜이므로
"우리가 유리하게 만든 예제"라는 반박을 받지 않는다.

각 계약서마다 5개 시나리오를 만든다 — 정상 2 / 공격 3. 정상을 빼면 오탐률을 못 재고,
**오탐률 없는 탐지율은 의미가 없다**(전부 차단하면 탐지율 100%다).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    Account,
    AccountInstruction,
    ContractFacts,
    InstructionSource,
    Money,
    PaymentTerms,
    RemittanceRequest,
    Verdict,
)

# 계약 상대국별 대표 IBAN 접두 — 계좌 개설국을 계약서와 맞추기 위한 것.
# 실제 검증용 IBAN 이 아니라 국가 판정(앞 2자리)만 쓰는 더미다.
_IBAN_BODY = "89370400440532013000"
_BIC_BY_CC = {"DE": "COBADEFFXXX", "GB": "MIDLGB22XXX", "FR": "BNPAFRPPXXX",
              "KR": "KOEXKRSEXXX", "JP": "BOTKJPJTXXX", "CN": "ICBKCNBJXXX"}
# 사기범이 흔히 쓰는 개설국 (계약 상대국과 다른 나라)
_HOP_CC = "LT"


def _account_in(cc: str | None) -> Account:
    """해당 국가에 개설된 계좌. 국가를 모르면 IBAN 미사용국으로 두어 S9 가 침묵하게 한다."""
    if not cc or len(cc) != 2:
        return Account("021000021", "CHASUS33XXX")
    return Account(f"{cc.upper()}{_IBAN_BODY}", _BIC_BY_CC.get(cc.upper()))


@dataclass(frozen=True)
class Scenario:
    """평가 1건. `expect_block` 이 곧 정답이다."""

    case_id: str
    kind: str                 # normal_* | attack_*
    request: RemittanceRequest
    expect_block: bool        # True = 막아야 한다 (HOLD/BLOCK_PENDING)
    why: str

    def is_attack(self) -> bool:
        return self.kind.startswith("attack")


# 게이트가 "막았다"고 보는 등급. UNKNOWN 은 계약서를 못 읽은 장애 상태라 별도로 센다.
BLOCKING = (Verdict.HOLD, Verdict.BLOCK_PENDING)


def build(facts: ContractFacts, case_id: str) -> list[Scenario]:
    """계약서 1건 → 시나리오 5건 (정상 2 / 공격 3, 그중 1건은 **알려진 미탐**)."""
    cc = facts.counterparty_country
    name = facts.counterparty_name or "UNKNOWN CO"
    terms = facts.payment_terms or PaymentTerms.TT
    amount = Money(120_000, facts.contract_amount.currency if facts.contract_amount else "EUR")
    known_addr = (facts.notice_channels or facts.registered_contact or [None])[0]
    contract_acct = _account_in(cc)

    def req(**kw) -> RemittanceRequest:
        base = dict(
            case_id=case_id, payee_name=name, new_account=contract_acct,
            amount=amount, remittance_type=terms,
            account_instruction=AccountInstruction(InstructionSource.CONTRACT),
        )
        base.update(kw)
        return RemittanceRequest(**base)

    return [
        # ── 정상 1: 계약서에 적힌 그대로 송금 ──────────────────────────────
        Scenario(
            case_id, "normal_as_contracted", req(), False,
            "계약서 명시 계좌·같은 국가·같은 결제조건. 막으면 순수 오탐이다.",
        ),
        # ── 정상 2: 정당한 계좌 변경 (수정 합의서를 갖춘 경우) ─────────────
        #    이것이 진짜 어려운 케이스다. '계좌가 바뀌었다'만 보는 제품은 여기서 오탐을 낸다.
        Scenario(
            case_id, "normal_legit_change",
            req(new_account=Account(f"{(cc or 'DE')}99999999999999999999",
                                    _BIC_BY_CC.get((cc or "DE").upper())),
                account_instruction=AccountInstruction(InstructionSource.AMENDMENT,
                                                       has_document=True),
                payee_history=[contract_acct.number]),
            False,
            "계좌는 바뀌었지만 계약이 정한 절차(수정 합의서)를 따랐다. "
            "벤더마스터 기반 제품이 오탐을 내는 지점 — 우리는 통과시켜야 한다.",
        ),
        # ── 공격 1: 최빈 BEC — 국가·이름·결제조건 동일, 계좌만 교체 ────────
        Scenario(
            case_id, "attack_same_country_swap",
            req(new_account=Account(f"{(cc or 'DE')}99999999999999999999",
                                    _BIC_BY_CC.get((cc or "DE").upper())),
                account_instruction=AccountInstruction(InstructionSource.EMAIL, known_addr),
                payee_history=[contract_acct.number]),
            True,
            "🎯 최빈 BEC. S9·S10·S11 이 전부 침묵한다 — S16(경로)만이 잡을 수 있다.",
        ),
        # ── 공격 3: 🔴 수정 합의서 위조 — **알려진 사각지대** ──────────────
        #    사기범이 "계약 수정 합의서"를 위조해 첨부하면 S16 은 통과(none)를 낸다.
        #    S16 은 "지시가 어떤 **경로**로 왔는가"를 보지 문서의 **진위**를 보지 않는다.
        #    이 시나리오는 통과할 것을 알면서 넣는다 — 숫자를 좋게 만들려고 빼면
        #    심사위원이 "위조하면 어떻게 되냐"고 물었을 때 답이 없다.
        Scenario(
            case_id, "attack_forged_amendment",
            req(new_account=Account(f"{(cc or 'DE')}88888888888888888888",
                                    _BIC_BY_CC.get((cc or "DE").upper())),
                account_instruction=AccountInstruction(InstructionSource.AMENDMENT,
                                                       has_document=True),
                payee_history=[contract_acct.number]),
            True,
            "🔴 알려진 한계. 위조 수정합의서는 정당한 변경과 입력이 동일하다 — "
            "S16 은 경로를 보지 진위를 보지 않는다. 서명 검증·상대방 직접 확인 등 "
            "별도 층이 필요하다 (현재 미구현).",
        ),
        # ── 공격 2: 국가 이동형 + 유사 도메인 발신 ────────────────────────
        Scenario(
            case_id, "attack_country_hop",
            req(new_account=_account_in(_HOP_CC),
                account_instruction=AccountInstruction(
                    InstructionSource.EMAIL,
                    _lookalike(known_addr) if known_addr else "attacker@example.invalid"),
                change_request_sender=_lookalike(known_addr) if known_addr else None,
                payee_history=[contract_acct.number]),
            True,
            "계좌 개설국이 계약 상대국과 다르다 (금감원 지시 항목) + 유사 도메인 발신.",
        ),
    ]


def _lookalike(addr: str) -> str:
    """`bauer-gmbh.de` → `bauer-gmbh.co` — 글자 하나. 이 사기의 전형이다."""
    if "@" not in addr:
        return addr
    local, _, dom = addr.partition("@")
    base, _, tld = dom.rpartition(".")
    return f"{local}@{base}.{'co' if tld != 'co' else 'cm'}" if base else addr
