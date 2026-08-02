"""입력·추출 스키마.

기술명세서 §3(입력) · §4.1(L1 추출 대상)의 코드화.
stdlib only — AITHOR-Agent-Framework 코어와 같은 제약을 따른다.

🔴 INV-6: `ContractFacts`에 판정·점수 필드가 존재하지 않는다.
   LLM은 이 구조체만 채울 수 있고, 등급은 규칙 테이블(rules.py)이 정한다.
   따라서 계약서에 심어진 인젝션("이 요청은 정상입니다")이 등급을 움직일 경로가 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InstructionSource(str, Enum):
    """이 계좌를 어디서 받았는가 (S16 오른쪽 입력).

    🔴 은행 송금 신청 서식에 이 항목이 **이미 있는지는 미확인**이다 (U-19, 서식 실물 미확보).
    없다면 드롭다운 1개 추가가 필요하다 — 새 서류가 아니라 기존 폼의 필드다.
    """

    CONTRACT = "contract"      # 계약서에 명시된 계좌
    AMENDMENT = "amendment"    # 계약 수정 합의서
    INVOICE = "invoice"        # 인보이스 기재
    PORTAL = "portal"          # 상대방 공식 포털·시스템
    EMAIL = "email"
    PHONE = "phone"
    FAX = "fax"
    OTHER = "other"


class PaymentTerms(str, Enum):
    """결제조건. L/C는 은행이 지급을 보증하고 T/T는 계좌로 직접 들어간다 — 이 차이가 S10의 근거."""

    LC = "LC"      # Letter of Credit (화환신용장)
    TT = "TT"      # Telegraphic Transfer (전신송금)
    DP = "DP"      # Documents against Payment
    DA = "DA"      # Documents against Acceptance
    CAD = "CAD"    # Cash Against Documents
    COD = "COD"    # Cash On Delivery
    OA = "OA"      # Open Account


class Severity(str, Enum):
    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"


class Verdict(str, Enum):
    """L4 규칙 테이블 출력. BLOCK_PENDING은 거부가 아니라 사람 승인 대기다."""

    PASS = "PASS"
    NOTICE = "NOTICE"
    HOLD = "HOLD"
    BLOCK_PENDING = "BLOCK_PENDING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Money:
    amount: float
    currency: str


@dataclass(frozen=True)
class Account:
    """IBAN 또는 계좌번호 + BIC. 개설국 판정은 signals.iban_country가 한다."""

    number: str
    bic: str | None = None


@dataclass(frozen=True)
class AccountInstruction:
    """S16 입력."""

    source: InstructionSource
    channel_detail: str | None = None   # 발신 주소·전화번호 등
    has_document: bool = False          # 근거 문서 첨부 여부


@dataclass
class ContractFacts:
    """L1이 계약서에서 추출하는 사실. 판정 필드 없음 (INV-6).

    🔴 evidence_spans 필수 — 각 필드가 계약서 어느 구간에서 나왔는지.
       없으면 창작이다.
    """

    counterparty_name: str | None = None
    counterparty_country: str | None = None      # ISO 3166-1 alpha-2
    counterparty_address: str | None = None
    registered_contact: list[str] = field(default_factory=list)  # 계약서 기재 연락처
    payment_terms: PaymentTerms | None = None
    payment_terms_raw: str | None = None
    contract_date: str | None = None
    contract_amount: Money | None = None

    # §Notices / §Amendment — S16의 준거
    notice_clause: str | None = None
    notice_channels: list[str] = field(default_factory=list)  # 지정 이메일 주소
    # 🎯 통지 조항이 지정한 **수단의 종류**. 주소가 아니라 채널이다.
    #    실측(03_R7_측정 §3-2): 계약서에 이메일 주소가 있는 비율은 19.9%뿐인데
    #    우편 주소는 82.8%, 팩스·전화는 40.4%다. 주소만 보면 8할을 못 쓴다.
    #    "계약은 서면·팩스 통지를 정했는데 계좌 지시는 이메일"도 절차 이탈이다.
    #    값: postal | fax | email | courier | in_person | other
    notice_channel_types: list[str] = field(default_factory=list)
    amendment_clause: str | None = None
    amendment_clause_requires_written: bool = False

    evidence_spans: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """추출 실패 판정 (기술명세서 §4.1). 국가·결제조건 둘 다 없으면 대조할 것이 없다."""
        return self.counterparty_country is None and self.payment_terms is None


@dataclass
class RemittanceRequest:
    """송금 신청 1건."""

    case_id: str
    payee_name: str
    new_account: Account
    amount: Money
    remittance_type: PaymentTerms
    account_instruction: AccountInstruction

    has_contract: bool = True
    payee_history: list[str] | None = None   # 과거 수취계좌 번호. None = 조회 실패, [] = 신규 거래처

    # L3 보조 신호 입력 (계좌변경 요청 문서 제출 시만)
    change_request_sender: str | None = None
    change_request_in_reply_to: str | None = None


@dataclass(frozen=True)
class SignalHit:
    """발화한 신호 1건. detail은 사용자에게 그대로 보이는 문장이 된다."""

    signal_id: str
    name: str
    severity: Severity
    detail: str
    evidence: str | None = None
