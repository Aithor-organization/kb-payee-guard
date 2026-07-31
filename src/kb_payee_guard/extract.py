"""L1 계약서 판독 — 추출기 3종 (A/B/C 베이스라인).

이 모듈의 존재 이유는 **AI 필연성을 수치로 증명**하는 것이다.

S16이 하는 계산은 `[계약이 허용한 경로 집합] ∩ [이번 지시가 온 경로]` 다.
오른쪽은 은행이 신청 폼으로 묻는다 — 결정론이다.
왼쪽은 계약서 자연어에만 있다. DB에도 없고, 고객에게 물을 수도 없다
(자기 계약서 §14를 외우고 있는 사람은 없다).

따라서 왼쪽을 못 뽑으면 S16이 존재할 수 없고, S16은 판정 축의 중심이다.
문제는 **조항을 찾는 것이 아니라 조항이 허용하는 경로를 판정하는 것**이다:

    "Any amendment shall be in writing signed by both parties"
        → 이메일 계좌 지시는 위반 (requires_written=True)
    "Either party may update banking details by notifying the other"
        → 이메일 지시가 정당 (requires_written=False)

둘 다 'writing/notify' 계열 단어를 갖는다. 키워드로는 못 가른다.
Baseline A가 정확히 여기서 무너지는지를 측정한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .models import ContractFacts, PaymentTerms


class Extractor(Protocol):
    """추출기 계약. A/B/C가 같은 인터페이스를 구현해야 비교가 성립한다."""

    name: str

    def extract(self, text: str) -> ContractFacts: ...


# ── 공통 어휘 ─────────────────────────────────────────────────────────────────

_PAYMENT_PATTERNS: list[tuple[re.Pattern, PaymentTerms]] = [
    (re.compile(r"\b(irrevocable\s+)?(documentary\s+)?letter\s+of\s+credit\b|\bL/?C\b|화환신용장", re.I), PaymentTerms.LC),
    (re.compile(r"\btelegraphic\s+transfer\b|\bT/?T\b|전신송금", re.I), PaymentTerms.TT),
    (re.compile(r"\bdocuments?\s+against\s+payment\b|\bD/?P\b", re.I), PaymentTerms.DP),
    (re.compile(r"\bdocuments?\s+against\s+acceptance\b|\bD/?A\b", re.I), PaymentTerms.DA),
    (re.compile(r"\bcash\s+against\s+documents?\b|\bCAD\b", re.I), PaymentTerms.CAD),
    (re.compile(r"\bopen\s+account\b", re.I), PaymentTerms.OA),
]

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# 조항 heading 은 계약마다 다르다 — 번호 체계도(§14 / Article 12 / Clause 8.3), 언어도.
_NOTICE_HEAD = re.compile(
    r"^\s*(?:§|Article|Clause|Section|제)?\s*[\dIVXA-Z.]{0,6}\s*[.)]?\s*"
    r"(Notices?|Notification|Communications?|통\s*지|통\s*보)\b.*$",
    re.I | re.M,
)
_AMEND_HEAD = re.compile(
    r"^\s*(?:§|Article|Clause|Section|제)?\s*[\dIVXA-Z.]{0,6}\s*[.)]?\s*"
    r"(Amendments?|Modifications?|Variation|Entire\s+Agreement|변\s*경|수\s*정)\b.*$",
    re.I | re.M,
)

# Baseline A가 "서면 요구"를 판정하려 쓰는 키워드.
# 🔴 이것이 A의 한계를 보여주는 지점이다 — 아래 두 문장을 못 가른다:
#      "shall be in writing signed by both parties"        (요구)
#      "may notify ... in writing or by email"             (선택지 중 하나)
_WRITTEN_KEYWORDS = re.compile(
    r"\bin\s+writing\b|\bwritten\s+(agreement|consent|instrument|notice)\b|서\s*면", re.I
)


def _clause_body(text: str, head: re.Match, max_chars: int = 1200) -> str:
    """heading 다음부터 다음 heading 또는 max_chars까지를 조항 본문으로 본다."""
    start = head.end()
    tail = text[start:start + max_chars]
    nxt = re.search(r"\n\s*(?:§|Article|Clause|Section|제)\s*[\dIVX]", tail)
    return (tail[: nxt.start()] if nxt else tail).strip()


# ── Baseline A — 키워드/정규식 ────────────────────────────────────────────────

@dataclass
class RegexExtractor:
    """A. LLM 없이 정규식·키워드만. 무료·즉시·결정론.

    이것이 충분하다면 AI는 불필요하다. 그 가설을 정면으로 시험한다.
    """

    name: str = "A-regex"

    def extract(self, text: str) -> ContractFacts:
        f = ContractFacts()
        spans: dict[str, str] = {}

        for pat, term in _PAYMENT_PATTERNS:
            m = pat.search(text)
            if m:
                f.payment_terms = term
                f.payment_terms_raw = m.group(0)
                spans["payment_terms"] = m.group(0)
                break

        f.registered_contact = list(dict.fromkeys(_EMAIL_RE.findall(text)))
        if f.registered_contact:
            spans["registered_contact"] = ", ".join(f.registered_contact[:3])

        nm = _NOTICE_HEAD.search(text)
        if nm:
            body = _clause_body(text, nm)
            f.notice_clause = body
            # 조항 본문에 있는 메일 주소만 통지 경로로 본다
            f.notice_channels = list(dict.fromkeys(_EMAIL_RE.findall(body)))
            spans["notice_clause"] = body[:200]

        am = _AMEND_HEAD.search(text)
        if am:
            body = _clause_body(text, am)
            f.amendment_clause = body
            # 🔴 A의 핵심 한계: 키워드 존재 = 요구 로 단정한다.
            #    "may notify in writing or by email"도 True가 된다.
            f.amendment_clause_requires_written = bool(_WRITTEN_KEYWORDS.search(body))
            spans["amendment_clause"] = body[:200]

        f.evidence_spans = spans
        return f


# ── Baseline B — 사람이 폼에 입력 ─────────────────────────────────────────────

@dataclass
class FormExtractor:
    """B. 계약서를 읽지 않고 사람이 폼에 직접 입력한다.

    "AI 없이 폼 하나 더 받으면 되지 않나"에 대한 대조군이다.
    구조상 계약서 본문을 보지 않으므로, 사용자가 모르거나 틀리게 아는 항목은 비어 있다.
    """

    name: str = "B-form"
    responses: dict[str, object] | None = None

    def extract(self, text: str) -> ContractFacts:  # noqa: ARG002 — 본문을 보지 않는 것이 요점
        r = self.responses or {}
        f = ContractFacts(
            counterparty_name=r.get("counterparty_name"),          # type: ignore[arg-type]
            counterparty_country=r.get("counterparty_country"),    # type: ignore[arg-type]
            payment_terms=r.get("payment_terms"),                  # type: ignore[arg-type]
            registered_contact=list(r.get("registered_contact", [])),  # type: ignore[arg-type]
            amendment_clause_requires_written=bool(r.get("amendment_clause_requires_written", False)),
            notice_channels=list(r.get("notice_channels", [])),     # type: ignore[arg-type]
        )
        f.evidence_spans = {"_source": "user_form"}   # 계약서 근거 없음 — 이것도 사실이다
        return f
