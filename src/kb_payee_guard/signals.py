"""L2 대조 신호 (결정론, LLM 없음) + L3 보조 신호.

기술명세서 §4.2 / §4.2-bis / §4.3의 코드화.

이 층은 순수 함수다. 입력이 같으면 출력이 항상 같다 — 튜닝할 가중치도 임계값도 없다.
신호의 `detail` 문자열이 곧 사용자에게 보이는 근거 문장이다 (판정과 설명이 같은 것에서 나온다).
"""

from __future__ import annotations

import re

from .models import (
    AccountInstruction,
    ContractFacts,
    InstructionSource,
    PaymentTerms,
    RemittanceRequest,
    Severity,
    SignalHit,
)

# ── S9 ────────────────────────────────────────────────────────────────────────

_IBAN_RE = re.compile(r"^([A-Z]{2})\d{2}[A-Z0-9]+$")


def iban_country(number: str, bic: str | None = None) -> str | None:
    """IBAN 앞 2자리 = ISO 3166-1 alpha-2 (ISO 13616-1).

    IBAN 미사용국(미국 등)은 SWIFT BIC 5~6번째 자리로 대체한다.
    둘 다 판정 불가면 None — 침묵이 아니라 '모른다'이며, 호출자가 신호를 띄우지 않는다.
    """
    compact = re.sub(r"\s+", "", number).upper()
    m = _IBAN_RE.match(compact)
    if m:
        return m.group(1)
    if bic and len(bic) >= 6:
        cc = bic[4:6].upper()
        if cc.isalpha():
            return cc
    return None


def check_s9(facts: ContractFacts, req: RemittanceRequest) -> SignalHit | None:
    """S9 CONTRACT_COUNTRY_MISMATCH — 금감원이 전 은행에 지시한 항목."""
    if facts.counterparty_country is None:
        return None
    acct_cc = iban_country(req.new_account.number, req.new_account.bic)
    if acct_cc is None:
        return None
    if acct_cc == facts.counterparty_country.upper():
        return None
    return SignalHit(
        "S9",
        "CONTRACT_COUNTRY_MISMATCH",
        Severity.HIGH,
        f"계약 상대방 소재국은 {facts.counterparty_country.upper()}인데 "
        f"수취계좌 개설국은 {acct_cc}입니다.",
        facts.evidence_spans.get("counterparty_country"),
    )


# ── S10 ───────────────────────────────────────────────────────────────────────

# (계약서 결제조건, 실제 송금방식) → severity.
# 🔴 방향이 비대칭이다. 안전한 쪽으로의 변경(T/T → L/C)은 경고하지 않는다 —
#    무조건 경고하면 사용자가 게이트를 끈다.
_S10_TABLE: dict[tuple[PaymentTerms, PaymentTerms], Severity] = {
    (PaymentTerms.LC, PaymentTerms.TT): Severity.HIGH,    # 지급보증 → 계좌 직입금
    (PaymentTerms.LC, PaymentTerms.DP): Severity.MEDIUM,
    (PaymentTerms.LC, PaymentTerms.DA): Severity.MEDIUM,
    (PaymentTerms.LC, PaymentTerms.OA): Severity.HIGH,
    (PaymentTerms.DP, PaymentTerms.TT): Severity.MEDIUM,  # 서류 통제 상실
    (PaymentTerms.DA, PaymentTerms.TT): Severity.MEDIUM,
    (PaymentTerms.CAD, PaymentTerms.TT): Severity.MEDIUM,
}

_TERMS_KO = {
    PaymentTerms.LC: "L/C(화환신용장)",
    PaymentTerms.TT: "T/T(전신송금)",
    PaymentTerms.DP: "D/P",
    PaymentTerms.DA: "D/A",
    PaymentTerms.CAD: "CAD",
    PaymentTerms.COD: "COD",
    PaymentTerms.OA: "Open Account",
}


def check_s10(facts: ContractFacts, req: RemittanceRequest) -> SignalHit | None:
    """S10 PAYMENT_TERMS_MISMATCH — 기존 제품 사용 확인 0건."""
    if facts.payment_terms is None:
        return None
    if facts.payment_terms == req.remittance_type:
        return None
    sev = _S10_TABLE.get((facts.payment_terms, req.remittance_type))
    if sev is None:
        return None  # 더 안전한 방향 또는 판정 근거 없음 → 침묵
    detail = (
        f"계약서 결제조건은 {_TERMS_KO[facts.payment_terms]}인데 "
        f"이번 송금은 {_TERMS_KO[req.remittance_type]}입니다."
    )
    if sev is Severity.HIGH and facts.payment_terms is PaymentTerms.LC:
        detail += " L/C는 은행이 지급을 보증하지만 T/T는 계좌로 바로 들어갑니다."
    return SignalHit("S10", "PAYMENT_TERMS_MISMATCH", sev, detail,
                     facts.evidence_spans.get("payment_terms"))


# ── S11 ───────────────────────────────────────────────────────────────────────

_LEGAL_SUFFIX = re.compile(
    r"\b(gmbh|ag|co|kg|ltd|limited|inc|corp|corporation|llc|plc|bv|nv|sa|srl|spa|pte|pty|kk)\b\.?",
    re.I,
)


def normalize_name(name: str) -> str:
    """법인격 접미사·구두점·공백을 제거한 비교용 형태.

    🔴 정규화가 과하면 다른 회사를 같다고 판정한다. 접미사만 걷어내고 어간은 건드리지 않는다.
    """
    s = name.lower()
    s = _LEGAL_SUFFIX.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def check_s11(facts: ContractFacts, req: RemittanceRequest) -> SignalHit | None:
    """S11 BENEFICIARY_NAME_MISMATCH — VoP와 커버가 겹친다."""
    if not facts.counterparty_name:
        return None
    if normalize_name(facts.counterparty_name) == normalize_name(req.payee_name):
        return None
    return SignalHit(
        "S11",
        "BENEFICIARY_NAME_MISMATCH",
        Severity.HIGH,
        f"계약서 상대방은 '{facts.counterparty_name}'인데 "
        f"수취인은 '{req.payee_name}'입니다.",
        facts.evidence_spans.get("counterparty_name"),
    )


# ── S12 ───────────────────────────────────────────────────────────────────────

def check_s12(facts: ContractFacts, req: RemittanceRequest,
              tolerance: float = 0.10) -> SignalHit | None:
    """S12 AMOUNT_EXCEEDS_CONTRACT. 통화가 다르면 환산하지 않고 침묵한다 —
    환율을 끌어오는 순간 결정론이 깨지고 '언제 환율인가'가 판정에 끼어든다."""
    if facts.contract_amount is None:
        return None
    if facts.contract_amount.currency != req.amount.currency:
        return None
    limit = facts.contract_amount.amount * (1 + tolerance)
    if req.amount.amount <= limit:
        return None
    return SignalHit(
        "S12",
        "AMOUNT_EXCEEDS_CONTRACT",
        Severity.MEDIUM,
        f"계약 금액은 {facts.contract_amount.amount:,.0f} {facts.contract_amount.currency}인데 "
        f"이번 송금은 {req.amount.amount:,.0f} {req.amount.currency}입니다.",
        facts.evidence_spans.get("contract_amount"),
    )


# ── S16 (판정 축의 중심) ───────────────────────────────────────────────────────

_WRITTEN_PATH = (InstructionSource.CONTRACT, InstructionSource.AMENDMENT)
_UNWRITTEN_PATH = (InstructionSource.EMAIL, InstructionSource.PHONE, InstructionSource.FAX)


def _addr_matches(detail: str | None, allowed: list[str]) -> bool:
    """발신 주소가 허용 목록에 있는가. 대소문자·공백만 정규화하고 도메인 부분일치는 하지 않는다 —
    부분일치를 허용하면 `bauer-gmbh.co`가 `bauer-gmbh.de`를 통과시킨다."""
    if not detail:
        return False
    d = detail.strip().lower()
    return any(d == a.strip().lower() for a in allowed)


def check_s16(facts: ContractFacts, instr: AccountInstruction) -> SignalHit:
    """S16 ACCOUNT_INSTRUCTION_PROVENANCE — 계좌 지시가 계약이 정한 경로로 왔는가.

    최빈 BEC는 같은 국가·같은 이름·같은 결제조건에서 계좌번호만 바꾼다. S9·S10·S11이
    전부 침묵한다. 그런데 **경로는 반드시 다르다** — 사기범 메일은 계약서가 정한 통지
    경로가 아니다. 계약서 §Notices·§Amendment는 체결 시점에 확정되어 사후 위조가 불가능하다.
    이 비대칭이 S16의 전부다.

    🔴 이 함수는 절대 None을 반환하지 않는다. 근거가 없으면 '근거가 없다'를 medium으로
       말한다 — 침묵은 통과와 구별되지 않기 때문이다 (TR-SIGNAL-HONESTY).
    """
    # 1. 계약서·수정합의서에서 온 계좌 — 조항과 무관하게 통과
    if instr.source in _WRITTEN_PATH:
        return SignalHit("S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.NONE,
                         "계좌 지시가 계약서 또는 수정 합의서에서 나왔습니다.")

    # 2. §Amendment가 서면 합의를 요구하는데 비서면 경로로 왔다 — 조항 위반
    if facts.amendment_clause_requires_written and instr.source in _UNWRITTEN_PATH:
        return SignalHit(
            "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.HIGH,
            f"계약서는 계좌 변경을 서면 합의로 제한하는데 이번 지시는 "
            f"{_SOURCE_KO[instr.source]}입니다.",
            facts.amendment_clause,
        )

    # 3. §Notices가 지정 경로를 명시 — 발신 주소 대조
    if facts.notice_channels and instr.source is InstructionSource.EMAIL:
        if _addr_matches(instr.channel_detail, facts.notice_channels):
            return SignalHit(
                "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.MEDIUM,
                "계약서가 지정한 통지 주소에서 왔지만, 계좌 변경 자체는 이메일 지시입니다.",
                facts.notice_clause,
            )
        return SignalHit(
            "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.HIGH,
            f"계약서가 지정한 통지 주소({', '.join(facts.notice_channels)})가 아닌 "
            f"'{instr.channel_detail or '미상'}'에서 왔습니다.",
            facts.notice_clause,
        )

    # 4. 🎯 S16-b fallback — 절차 조항이 없을 때 계약서 기재 연락처를 준거로 쓴다.
    #
    #    왜 필요한가: 3번까지만 있으면 §Notices·§Amendment가 없는 계약서에서 S16이
    #    무조건 medium이 되고, R7이 전건 HOLD를 낸다. 게이트가 사실상 꺼진다.
    #    조항 존재율(R-7)을 측정하기 전에는 이것이 다수 경로일 수 있다.
    #
    #    당사자 표기(담당자·이메일·주소)는 계약의 필수 구성요소라 절차 조항보다
    #    존재율이 높다. 조항이 없어도 "계약서에 적힌 그 사람에게서 온 것인가"는 물을 수 있다.
    if facts.registered_contact and instr.source is InstructionSource.EMAIL:
        if not _addr_matches(instr.channel_detail, facts.registered_contact):
            return SignalHit(
                "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.HIGH,
                f"계약서에 절차 조항은 없지만, 기재된 연락처"
                f"({', '.join(facts.registered_contact)})가 아닌 "
                f"'{instr.channel_detail or '미상'}'에서 계좌 변경 지시가 왔습니다.",
                facts.evidence_spans.get("registered_contact"),
            )
        return SignalHit(
            "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.MEDIUM,
            "계약서에 계좌 변경 절차 조항이 없습니다. 지시는 계약서 기재 연락처에서 왔지만 "
            "이메일만으로는 근거가 약합니다.",
        )

    # 5. 인보이스 단독 — 인보이스는 위조 가능하다
    if instr.source is InstructionSource.INVOICE:
        return SignalHit("S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.MEDIUM,
                         "계좌 근거가 인보이스뿐입니다. 인보이스는 위조 가능합니다.")

    # 6. 조항도 없고 기재 연락처도 없다 — 근거 부재. 침묵하지 않는다.
    return SignalHit(
        "S16", "ACCOUNT_INSTRUCTION_PROVENANCE", Severity.MEDIUM,
        f"계약서에 계좌 변경 절차 조항이 없고, 이번 지시는 {_SOURCE_KO[instr.source]}입니다.",
    )


_SOURCE_KO = {
    InstructionSource.CONTRACT: "계약서",
    InstructionSource.AMENDMENT: "수정 합의서",
    InstructionSource.INVOICE: "인보이스",
    InstructionSource.PORTAL: "상대방 공식 포털",
    InstructionSource.EMAIL: "이메일",
    InstructionSource.PHONE: "전화",
    InstructionSource.FAX: "팩스",
    InstructionSource.OTHER: "기타 경로",
}


# ── S5 ────────────────────────────────────────────────────────────────────────

# FATF "High-Risk Jurisdictions subject to a Call for Action" (블랙리스트).
# 이 3개국은 오랫동안 고정되어 있어 하드코딩해도 stale 위험이 낮다.
#
# 🔴 그레이리스트("Jurisdictions under Increased Monitoring")는 FATF 총회마다
#    바뀐다. 여기 박아두면 반드시 낡는다 — 외부 파일로 주입한다.
#    주입이 없으면 블랙리스트만으로 판정하고, 그 사실을 감사 로그에 남긴다.
FATF_CALL_FOR_ACTION = frozenset({"KP", "IR", "MM"})


def check_s5(facts: ContractFacts, req: RemittanceRequest,
             extra_high_risk: frozenset[str] | None = None) -> SignalHit | None:
    """S5 HIGH_RISK_JURISDICTION — 계좌 개설국이 고위험 관할인가.

    🔴 이 신호는 본래 기술명세서에 **정의가 없었다.** R11이 `s.S5`를 참조하는데
       S5를 정의한 절이 문서 어디에도 없어, R11은 v3.0의 R7·R8과 같은 dead rule
       이었다 — T15(도달성 검사)를 도입해 그 결함을 막겠다고 선언한 바로 그 문서에서.
       구현 과정에서 발견해 여기서 정의한다.

    등급이 NOTICE인 이유: 고위험 관할이라는 사실만으로는 사기가 아니다.
    계약서와 전부 일치하는데 관할만 고위험이면 차단이 아니라 고지가 맞다.
    """
    high_risk = FATF_CALL_FOR_ACTION | (extra_high_risk or frozenset())
    acct_cc = iban_country(req.new_account.number, req.new_account.bic)
    if acct_cc is None or acct_cc not in high_risk:
        return None
    return SignalHit(
        "S5", "HIGH_RISK_JURISDICTION", Severity.MEDIUM,
        f"수취계좌 개설국 {acct_cc}는 FATF 고위험 관할입니다.",
    )


# ── L3 보조 신호 + S1 트리거 ──────────────────────────────────────────────────

_HOMOGLYPH_CHAR = str.maketrans({"0": "o", "1": "l", "5": "s", "3": "e"})


def _fold_homoglyph(s: str) -> str:
    """시각적으로 같아 보이는 글자를 접는다. `rn`→`m`은 2글자→1글자라 별도 처리."""
    return s.replace("rn", "m").translate(_HOMOGLYPH_CHAR)


def _edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check_m1(facts: ContractFacts, req: RemittanceRequest) -> SignalHit | None:
    """M1 DOMAIN_LOOKALIKE — 계약서 기재 도메인 대비 편집거리·homoglyph·TLD 치환.

    v3에서 강화됨: v2는 '기존 거래 도메인'과 비교해 이력이 필요했다.
    v3는 계약서 기재 연락처와 비교한다 — 이력 불필요.
    """
    sender = req.change_request_sender
    if not sender or "@" not in sender or not facts.registered_contact:
        return None
    dom = sender.split("@")[-1].lower()
    for contact in facts.registered_contact:
        if "@" not in contact:
            continue
        ref = contact.split("@")[-1].lower()
        if dom == ref:
            return None  # 정확히 일치 → 신호 없음
    for contact in facts.registered_contact:
        if "@" not in contact:
            continue
        ref = contact.split("@")[-1].lower()
        d = _edit_distance(_fold_homoglyph(dom), _fold_homoglyph(ref))
        same_stem = dom.split(".")[0] == ref.split(".")[0]
        if 0 < d <= 2 or same_stem:
            return SignalHit(
                "M1", "DOMAIN_LOOKALIKE", Severity.HIGH,
                f"발신 도메인 '{dom}'이 계약서 기재 도메인 '{ref}'과 유사하지만 다릅니다.",
                contact,
            )
    return None


def check_m2(req: RemittanceRequest) -> SignalHit | None:
    """M2 REPLY_CHAIN_BREAK — In-Reply-To / References 헤더 단절."""
    if req.change_request_sender is None:
        return None
    if req.change_request_in_reply_to:
        return None
    return SignalHit("M2", "REPLY_CHAIN_BREAK", Severity.MEDIUM,
                     "계좌 변경 요청 메일이 기존 대화 스레드에 이어지지 않습니다.")


def check_s1(req: RemittanceRequest) -> SignalHit | None:
    """S1 신규 수취계좌 — 🔴 트리거일 뿐 판별자가 아니다. 정상 변경도 이력이 없다.

    payee_history 의미 구분 (기술명세서 §4.3):
      None → 조회 실패/미연동 → 비활성 + 감사 기록
      []   → 신규 거래처      → 비활성 ('변경'이 아니다)
    """
    if req.payee_history is None or req.payee_history == []:
        return None
    if req.new_account.number in req.payee_history:
        return None
    return SignalHit("S1", "NEW_PAYEE_ACCOUNT", Severity.MEDIUM,
                     "과거 송금 이력에 없는 새 계좌입니다.")
