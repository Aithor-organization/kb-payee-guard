#!/usr/bin/env python3.12
"""브라우저에서 게이트를 직접 눌러 보는 **로컬 데모 사이트** (stdlib only).

    python3.12 scripts/demo_server.py      →  http://127.0.0.1:8765

## 이게 무엇이고 무엇이 아닌가

🔴 **은행 연동도, 프로덕션 REST API 도 아니다.** 판정 엔진(`rules.evaluate`)을 손으로
눌러 볼 수 있게 감싼 **로컬 확인용 사이트**다. 인증·영속·감사원장·동시성 처리가 없고
127.0.0.1 에만 바인딩한다. README 의 "REST API·송금 신청 화면 미구현(P7)" 은 그대로다.

## 왜 stdlib 만 쓰나

코어가 `pip install` 없이 도는 것이 이 저장소의 전제다(README §직접 돌려보기).
데모 하나 때문에 Flask 를 끌어오면 그 전제가 깨진다. `http.server` 로 충분하다.

## API 키를 화면에서 받는다 — 다루는 방식

`설정`에서 사용자가 OpenAI 키를 넣으면 그 키로 계약서 추출이 돈다.
🔴 **메모리에만 둔다**: 파일·로그·응답 어디에도 원문을 쓰지 않는다. 상태 조회는
`sk-…` + 뒤 4자만 돌려주고, 프로세스를 끄면 사라진다. 지우기 버튼도 둔다.
`.env`/환경변수의 키가 이미 있으면 그것을 쓰고, 화면 입력이 그보다 우선한다.

## 계약서는 어디서 오나

`data/demo/mock_contract.txt` (목업 무역계약서). **키가 있으면** 이 원문을 LLM 추출기에
넣어 사실을 뽑고, **없으면** 같은 계약서를 사람이 읽고 옮겨 적은 값(`_FALLBACK_FACTS`)을 쓴다.
→ 키가 없어도 사이트는 완전히 동작하며, 어느 경로를 썼는지 매 판정마다 화면에 표시한다.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_payee_guard import rules                                     # noqa: E402
from kb_payee_guard.models import (                                  # noqa: E402
    Account, AccountInstruction, ContractFacts, InstructionSource, Money,
    PaymentTerms, RemittanceRequest,
)

CONTRACT_PATH = ROOT / "data" / "demo" / "mock_contract.txt"
PORT = int(os.environ.get("PORT", "8765"))

# ── API 키 보관 ────────────────────────────────────────────────────────────────
#   🔴 프로세스 메모리에만 둔다. 디스크·로그·응답 본문 어디에도 원문이 나가지 않는다.
#      ThreadingHTTPServer 라 여러 요청이 동시에 읽고 쓸 수 있어 Lock 을 건다.
_key_lock = threading.Lock()
_session_key: str | None = None

# ── 업로드된 계약서 ────────────────────────────────────────────────────────────
#   🔴 키와 같은 정책 — **메모리에만** 둔다. 디스크에 쓰지 않는다.
#      추출은 업로드 시 **1회만** 하고 결과를 캐시한다. 판정마다 LLM 을 다시 부르면
#      비용과 지연이 판정 횟수에 비례해 늘어나는데, 계약서가 바뀌지 않았으니 의미가 없다.
_doc_lock = threading.Lock()
_session_doc: dict | None = None          # {"name","text","facts","origin"}
MAX_DOC_BYTES = 400_000                   # 400KB — 계약서 한 건으로 충분하고 남는다


def active_key() -> tuple[str | None, str]:
    """(키, 출처). 화면 입력이 환경변수보다 우선한다."""
    with _key_lock:
        if _session_key:
            return _session_key, "session"
    env = os.environ.get("OPENAI_API_KEY")
    return (env, "env") if env else (None, "none")


def mask(k: str) -> str:
    """`sk-…a1b2` — 앞 3자와 뒤 4자만. 나머지는 절대 밖으로 내보내지 않는다."""
    return f"{k[:3]}…{k[-4:]}" if len(k) > 10 else "sk-…"


def key_status() -> dict:
    k, src = active_key()
    return {"present": bool(k), "masked": mask(k) if k else None, "source": src,
            "mode": "LLM 추출" if k else "수동 라벨"}


# 목업 계약서를 사람이 읽고 옮겨 적은 사실 — 키 없이 돌릴 때 쓴다.
# 🔴 이 값들은 LLM 이 뽑은 것이 아니라 **손으로 라벨링한 것**이다. 화면에 그렇게 표시한다.
_FALLBACK_FACTS = dict(
    counterparty_name="BAUER Maschinenbau GmbH",
    counterparty_country="DE",
    registered_contact=["ap@bauer-gmbh.de"],
    notice_channel_types=["POSTAL", "COURIER", "EMAIL"],
    notice_channels=["ap@bauer-gmbh.de"],
    payment_terms=PaymentTerms.LC,
    contract_date="2023-04-11",
    contract_amount=Money(184_500.0, "EUR"),
    amendment_clause=("14.3 any change of the bank account specified in Article 4 shall be "
                      "effective only upon a written amendment executed by both Parties"),
    amendment_clause_requires_written=True,
)


def extract_facts(text: str) -> tuple[ContractFacts, str]:
    """임의 계약서 원문 → 사실. **API 키가 반드시 필요하다.**

    목업 계약서에는 사람이 옮겨 적은 값(`_FALLBACK_FACTS`)이 있지만, 사용자가 올린
    계약서에는 그런 것이 있을 수 없다. 키가 없으면 추출 자체가 불가능하므로
    조용히 빈 사실로 넘어가지 않고 **명시적으로 실패**시킨다 —
    빈 사실로 판정하면 전부 `UNKNOWN` 이 나오는데 그게 "판정했다"로 보이면 안 된다.
    """
    key, _ = active_key()
    if not key:
        raise RuntimeError("계약서를 읽으려면 OpenAI API 키가 필요합니다. 설정에서 등록하세요.")
    prev = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = key
        from kb_payee_guard.llm_extract import LLMExtractor
        return LLMExtractor().extract(text), "LLM 추출 · gpt-4o-mini (업로드 계약서)"
    finally:
        if prev is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prev


def load_facts() -> tuple[ContractFacts, str]:
    """계약서 → 사실. 업로드본이 있으면 그것(추출 캐시), 없으면 목업."""
    with _doc_lock:
        if _session_doc:
            return _session_doc["facts"], _session_doc["origin"]
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    key, src = active_key()
    if key:
        prev = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEY"] = key
            from kb_payee_guard.llm_extract import LLMExtractor
            where = "설정에 입력한 키" if src == "session" else "환경변수 키"
            return LLMExtractor().extract(text), f"LLM 추출 · gpt-4o-mini ({where})"
        except Exception as exc:                                   # noqa: BLE001
            # 🔴 예외 문자열에 키가 섞여 나갈 수 있으므로 **타입 이름만** 남긴다.
            print(f"  LLM 추출 실패 → 수동 라벨로 대체: {type(exc).__name__}")
            return (ContractFacts(**_FALLBACK_FACTS),
                    f"수동 라벨 (LLM 추출 실패: {type(exc).__name__})")
        finally:
            if prev is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev
    return ContractFacts(**_FALLBACK_FACTS), "수동 라벨 (API 키 없음 — 추출기 미사용)"


# ── 시나리오 프리셋 ────────────────────────────────────────────────────────────
SCENARIOS = {
    "normal": {
        "label": "계약서대로 송금", "risk": "normal",
        "desc": "계약서 §4 의 독일 LBBW 계좌로, 계약서가 정한 L/C 로 보낸다.",
        "form": dict(account="DE44600501010002034567", bic="SOLADEST600",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="CONTRACT", channel_detail="", sender="", in_reply_to=""),
    },
    "legit_change": {
        "label": "적법한 계좌 변경", "risk": "normal",
        "desc": "양측이 서명한 수정합의서로 계좌를 바꿨다. 국가·결제조건은 그대로.",
        "form": dict(account="DE89370400440532013000", bic="COBADEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="AMENDMENT", channel_detail="", sender="", in_reply_to=""),
    },
    "bec_swap": {
        "label": "같은 나라, 계좌만 교체", "risk": "attack",
        "desc": "국가·이름·결제조건 전부 그대로. 이메일 한 통으로 계좌만 바꿔 달라고 한다. 가장 흔한 형태다.",
        "form": dict(account="DE12500105170648489890", bic="INGDDEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "bec_hop": {
        "label": "제3국 계좌 + 결제조건 변경", "risk": "attack",
        "desc": "독일 회사인데 리투아니아 계좌, L/C 였는데 T/T 로. 금감원 지시 항목에 해당한다.",
        "form": dict(account="LT121000011101001047", bic="REVOLT21",
                     amount="184500", currency="EUR", remittance_type="TT",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "forged": {
        "label": "위조 수정합의서", "risk": "gap",
        "desc": "가짜 수정합의서로 절차를 지킨 것처럼 꾸민다. 이 게이트는 못 막는다 — 알려진 사각지대다.",
        "form": dict(account="DE12500105170648489890", bic="INGDDEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="AMENDMENT", channel_detail="", sender="", in_reply_to=""),
    },
}


# 규칙 테이블을 사람이 읽을 수 있게 — 판정에 **쓰였지만 발화하지 않은** 규칙까지 보여준다.
#   "왜 이 규칙이 아니라 저 규칙인가" 는 발화한 규칙만 봐서는 답할 수 없다.
_RULE_DESC = {
    "R1": ("판정 불가", "계약서 부재 또는 추출 실패"),
    "R2": ("송금 보류", "계좌 지시가 계약 절차 조항을 위반한 경로로 옴 (최빈 BEC)"),
    "R3": ("송금 보류", "계약 상대방 소재국과 계좌 개설국 불일치"),
    "R4": ("송금 보류", "결제조건이 위험한 방향으로 전환됨 (L/C → T/T 등)"),
    "R5": ("송금 보류", "계약 수익자명과 수취인명 불일치"),
    "R6": ("송금 보류", "발신 도메인이 계약서 기재 도메인과 유사하지만 다름"),
    "R7": ("보류", "계좌 지시 근거가 약함 (절차 조항 부재 또는 인보이스 단독)"),
    "R8": ("보류", "송금액이 계약 금액을 초과"),
    "R9": ("보류", "근거 서류는 갖췄으나 동봉 메일이 수상"),
    "R11": ("참고", "신규 수취계좌 (트리거일 뿐 판별자 아님)"),
    "R0": ("이상 없음", "발화한 위험 신호 없음 — 계약이 정한 절차와 일치"),
}

_SIGNAL_DESC = {
    "S16": "계좌 지시가 계약이 정한 경로(§Notices·§Amendment)로 왔는가 — 이 제품의 판정 축",
    "S9":  "계약 상대방 소재국 ≠ 수취계좌 개설국 (금감원 지시 항목)",
    "S10": "계약서 결제조건 ≠ 이번 송금 방식 (방향 구분 — T/T→L/C 는 침묵)",
    "S11": "계약서 수익자명 ≠ 수취인명",
    "S12": "송금액이 계약 금액을 초과",
    "S1":  "신규 수취계좌 — 트리거일 뿐 판별자가 아니다",
    "S5":  "계좌 지시 근거 서류 유형",
    "M1":  "발신 도메인이 계약서 기재 도메인과 유사(편집거리·homoglyph·TLD 치환)",
    "M2":  "계좌 변경 요청 메일이 기존 스레드에 이어지지 않음 (In-Reply-To 부재)",
}


def audit_trail(facts: ContractFacts, req: RemittanceRequest, d) -> dict:
    """🔴 HITL 이 할루시네이션을 직접 잡을 수 있게 **전 단계를 그대로 편다**.

    금융에서 "AI 가 그렇게 판단했다" 는 근거가 아니다. 사람이 다음 사슬을
    **한 칸씩 되짚을 수 있어야** 한다:

        계약서 원문 → (근거 구간) → 추출된 사실 → (신호) → 발화 → (규칙) → 판정

    각 칸마다 "무엇을 근거로 이 값이 되었는가" 를 원문 그대로 붙인다.
    특히 `evidence_spans` 는 **LLM 이 원문에서 복사한 구간**이고,
    `llm_extract._verify_spans` 가 원문에 실재하는지 이미 대조한 값이다 —
    사람은 그 구간을 계약서에서 찾아 눈으로 확인만 하면 된다.
    """
    fired = {h.signal_id for h in d.hits}
    spans = facts.evidence_spans or {}

    # ① 추출된 사실 — 값 + 근거 구간
    FIELDS = [("counterparty_name", "계약 상대방(수취인)"),
              ("counterparty_country", "상대방 소재국"),
              ("payment_terms", "계약 결제조건"),
              ("contract_amount", "계약 금액"),
              ("notice_channel_types", "§Notices 통지 경로"),
              ("registered_contact", "계약서 기재 연락처"),
              ("amendment_clause", "§Amendment 변경 조항"),
              ("amendment_clause_requires_written", "변경에 서면 요구")]
    extracted = []
    for key, label in FIELDS:
        v = getattr(facts, key, None)
        extracted.append({
            "field": key, "label": label,
            "value": (v.value if hasattr(v, "value") else
                      (f"{v.amount:,.0f} {v.currency}" if hasattr(v, "currency") else
                       (list(v) if isinstance(v, (list, tuple)) else v))),
            "evidence": spans.get(key),        # 🔴 원문에서 복사·대조된 구간
        })

    # ② 신호 — 발화한 것 + 발화하지 않은 것
    signals = [{"id": h.signal_id, "name": h.name, "severity": h.severity.name,
                "fired": True, "what": _SIGNAL_DESC.get(h.signal_id, ""),
                "detail": h.detail, "evidence": h.evidence} for h in d.hits]
    for sid, what in _SIGNAL_DESC.items():
        if sid not in fired:
            signals.append({"id": sid, "name": "", "severity": "NONE",
                            "fired": False, "what": what, "detail": None, "evidence": None})

    # ③ 규칙 — 어떤 규칙이 적중했고 나머지는 왜 아닌가
    rules_tbl = [{"id": rid, "verdict": _RULE_DESC[rid][0], "cond": _RULE_DESC[rid][1],
                  "matched": rid == d.rule_id}
                 for rid in _RULE_DESC if rid in set(rules.RULE_IDS)]

    return {
        "chain": ["계약서 원문", "근거 구간 대조", "추출된 사실", "신호 산출", "규칙 테이블", "판정"],
        "input": {
            "수취 계좌": req.new_account.number, "BIC": req.new_account.bic,
            "금액": f"{req.amount.amount:,.0f} {req.amount.currency}",
            "송금 방식": req.remittance_type.value if req.remittance_type else None,
            "계좌 지시 출처": req.account_instruction.source.name,
            "지시가 온 경로": req.account_instruction.channel_detail,
            "메일 발신자": req.change_request_sender,
            "메일 스레드(In-Reply-To)": req.change_request_in_reply_to or "(없음 — 새 메일)",
        },
        "extracted": extracted,
        "signals": signals,
        "rules": rules_tbl,
        "matched_rule": d.rule_id,
        "span_check": {
            "total": len([e for e in extracted if e["value"] not in (None, [], "")]),
            "with_evidence": len([e for e in extracted if e["evidence"]]),
            "note": ("evidence 는 LLM 이 원문에서 **복사**한 구간이며 "
                     "`llm_extract._verify_spans` 가 원문 실재 여부를 이미 대조했습니다. "
                     "원문에 없으면 그 필드는 버려집니다 — 창작이기 때문입니다."),
        },
    }


def judge(form: dict) -> dict:
    facts, origin = load_facts()
    req = RemittanceRequest(
        case_id=form.get("case_id") or "DEMO-0001",
        payee_name=facts.counterparty_name or "BAUER Maschinenbau GmbH",
        new_account=Account(number=form["account"].replace(" ", ""), bic=form.get("bic") or None),
        amount=Money(float(form.get("amount") or 0), form.get("currency") or "EUR"),
        remittance_type=PaymentTerms[form.get("remittance_type", "TT")],
        account_instruction=AccountInstruction(
            source=InstructionSource[form.get("source", "EMAIL")],
            channel_detail=form.get("channel_detail") or None),
        has_contract=True,
        change_request_sender=form.get("sender") or None,
        change_request_in_reply_to=form.get("in_reply_to") or None,
    )
    d = rules.evaluate(facts, req)
    return {
        "verdict": d.verdict.value, "rule": d.rule_id, "reasons": list(d.reasons()),
        "audit": audit_trail(facts, req, d),
        "signals": [f"{h.signal_id} {h.name} ({h.severity.name})" for h in d.hits],
        "facts_origin": origin,
        "facts": {"상대방": facts.counterparty_name, "소재국": facts.counterparty_country,
                  "결제조건": facts.payment_terms.value if facts.payment_terms else None,
                  "통지 경로": facts.notice_channel_types,
                  "변경에 서면 요구": facts.amendment_clause_requires_written},
    }


# ── 화면 ──────────────────────────────────────────────────────────────────────
#
#  디자인 근거는 impeccable-design-system + AI-research-SKILLs 감사 결과를 따른다:
#   · KB 노란색은 **강조에만** — 마크·주 버튼·핵심 입력·hero 하이라이트.
#     판정 결과에는 쓰지 않는다 (브랜드색이 상태색과 섞이면 위험 신호가 죽는다).
#   · 그림자 0 — 깊이는 1px 보더로 (Revolut "ZERO shadows" · Wise "ring only" 계열).
#   · 컬러 border-left 는 1px 까지 (craft-floor Refuse: "1px 초과 금지").
#   · 금융 숫자는 tabular numeral (stripe DESIGN.md §3 `tnum`).
#   · 배지는 bg 색상 ~9% / border ~34% / 진한 텍스트 (stripe §4 공식).
#   · focus 는 outline 2px + offset 2px, `transition: all` 금지, reduced-motion 대체 경로.
#   · 아이콘은 전부 인라인 SVG — 이모지는 OS 마다 모양이 달라 금융 UI 의 신뢰를 깎는다.
#   · 외부 리소스 0(폰트·아이콘·스크립트 전부 인라인) — 폐쇄망에서도 그대로 뜬다.
PAGE = """<!doctype html><html lang=ko><meta charset=utf-8>
<title>KB Payee Guard — 계약서로 검증하는 해외송금 게이트</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{
  --kb:#FFBC00; --kb-d:#F0A800;
  --ink:#1C1A16; --ink-2:#4C4941; --ink-3:#7C7870;
  --bg:#F5F4F2; --sf:#FFF; --line:#E5E2DD; --line-2:#F0EEEA;
  --danger:#A81E28; --warn:#8A5600; --hold:#454B53; --safe:#0B5F49;
  --r:10px; --r-s:7px; --ease:cubic-bezier(.23,1,.32,1);
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--sf);color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  -webkit-font-smoothing:antialiased}
@media(prefers-reduced-motion:reduce){*{transition:none!important}html{scroll-behavior:auto}}
.in{max-width:1160px;margin:0 auto;padding:0 24px}
code{font-family:var(--mono);font-size:.92em}

/* GNB */
.gnb{position:sticky;top:0;z-index:40;background:rgba(255,255,255,.95);
  border-bottom:1px solid var(--line)}
.gnb .in{height:60px;display:flex;align-items:center;gap:12px}
.mk{width:30px;height:30px;border-radius:8px;background:var(--kb);display:grid;place-items:center;flex:none}
.bn{font-size:16px;font-weight:700;letter-spacing:-.015em;white-space:nowrap}
nav{margin-left:26px;display:flex;gap:3px}
nav a{padding:7px 11px;border-radius:6px;font-size:13.5px;color:var(--ink-2);text-decoration:none;
  transition:background 150ms var(--ease),color 150ms var(--ease)}
nav a:hover{background:var(--bg);color:var(--ink)}
@media(max-width:860px){nav{display:none}}
.rt{margin-left:auto;display:flex;align-items:center;gap:9px}
.chip{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--ink-2);
  border:1px solid var(--line);border-radius:20px;padding:5px 11px}
.chip .d{width:6px;height:6px;border-radius:50%;background:#B9BDC3;flex:none}
.chip.on .d{background:var(--safe)}
@media(max-width:520px){.chip{display:none}}
button{font-family:inherit}
.btn-s{border:1px solid var(--line);background:var(--sf);color:var(--ink-2);border-radius:var(--r-s);
  padding:7px 13px;font:600 13px/1 inherit;cursor:pointer;min-height:34px;
  transition:background 150ms var(--ease),border-color 150ms var(--ease)}
.btn-s:hover{background:var(--bg);border-color:#CFCBC4}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{
  outline:2px solid var(--kb-d);outline-offset:2px}

/* HERO */
.hero{padding:76px 0 64px;border-bottom:1px solid var(--line);
  background:radial-gradient(1100px 300px at 50% -140px,rgba(255,188,0,.13),transparent 70%)}
.eyebrow{font-size:12.5px;font-weight:600;color:var(--warn);letter-spacing:.02em;margin-bottom:14px}
h1{margin:0 0 20px;font-size:44px;line-height:1.2;letter-spacing:-.032em;font-weight:700;max-width:20ch}
h1 em{font-style:normal;background:linear-gradient(transparent 62%,rgba(255,188,0,.45) 62%)}
.lead{font-size:17px;line-height:1.72;color:var(--ink-2);max-width:62ch;margin:0 0 30px}
.cta{display:flex;gap:10px;flex-wrap:wrap}
.btn-p{background:var(--kb);color:#231A00;border:0;border-radius:var(--r-s);padding:0 22px;
  min-height:46px;font:700 15px/1 inherit;cursor:pointer;display:inline-flex;align-items:center;gap:8px;
  text-decoration:none;transition:background 150ms var(--ease)}
.btn-p:hover{background:var(--kb-d)}
.btn-o{border:1px solid #D6D2CB;background:var(--sf);color:var(--ink);border-radius:var(--r-s);
  padding:0 20px;min-height:46px;font:600 15px/1 inherit;cursor:pointer;display:inline-flex;
  align-items:center;text-decoration:none;transition:background 150ms var(--ease)}
.btn-o:hover{background:var(--bg)}
@media(max-width:640px){h1{font-size:31px}.hero{padding:52px 0 44px}}

/* SECTION */
section{padding:72px 0;border-bottom:1px solid var(--line)}
section.alt{background:var(--bg)}
.sh{font-size:12.5px;font-weight:700;color:var(--warn);letter-spacing:.05em;margin-bottom:11px}
h2{margin:0 0 14px;font-size:29px;line-height:1.34;letter-spacing:-.026em;font-weight:700}
.sub{font-size:15.5px;color:var(--ink-2);max-width:68ch;margin:0 0 32px;line-height:1.74}
@media(max-width:640px){h2{font-size:24px}section{padding:52px 0}}

.pr{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:860px){.pr{grid-template-columns:1fr}}
.pc{background:var(--sf);border:1px solid var(--line);border-radius:var(--r);padding:22px}
.pc .n{font:700 27px/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.02em;margin-bottom:9px}
.pc h3{margin:0 0 7px;font-size:14.5px;font-weight:700}
.pc p{margin:0;font-size:13.5px;color:var(--ink-2);line-height:1.68}

.wrapx{overflow-x:auto}
.tbl{width:100%;border-collapse:collapse;font-size:13.5px;background:var(--sf);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;min-width:640px}
.tbl th{text-align:left;padding:11px 15px;font-size:12px;font-weight:700;color:var(--ink-3);
  background:var(--bg);border-bottom:1px solid var(--line)}
.tbl td{padding:12px 15px;border-bottom:1px solid var(--line-2);color:var(--ink-2);vertical-align:top}
.tbl tr:last-child td{border-bottom:0}
.tbl tr.us td{background:rgba(255,188,0,.07);color:var(--ink);font-weight:600}

.flow{display:grid;grid-template-columns:1fr auto 1fr;gap:20px;align-items:center;
  background:var(--sf);border:1px solid var(--line);border-radius:var(--r);padding:26px}
@media(max-width:860px){.flow{grid-template-columns:1fr;gap:14px}.flow .ar{transform:rotate(90deg);justify-self:center}}
.fb{border:1px solid var(--line);border-radius:var(--r-s);padding:16px 18px}
.fb h4{margin:0 0 10px;font-size:12px;font-weight:700;color:var(--ink-3);letter-spacing:.03em}
.fb dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:5px 13px;font-size:13px}
.fb dt{color:var(--ink-3);white-space:nowrap}
.fb dd{margin:0;font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
.q{margin-top:22px;padding:18px 20px;border:1px solid rgba(255,188,0,.5);background:rgba(255,188,0,.06);
  border-radius:var(--r);font-size:16.5px;font-weight:700;letter-spacing:-.015em;text-align:center}

.mt{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
@media(max-width:860px){.mt{grid-template-columns:repeat(2,1fr)}}
.mc{background:var(--sf);border:1px solid var(--line);border-radius:var(--r);padding:18px}
.mc .v{font:700 25px/1.15 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.025em}
.mc .u{font-size:15px}
.mc .k{font-size:12px;color:var(--ink-3);margin-top:7px;line-height:1.55}
.note{margin-top:16px;font-size:12.5px;color:var(--ink-3);line-height:1.75;max-width:78ch}

/* DEMO */
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;align-items:start}
@media(max-width:940px){.grid{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--sf);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.hd{padding:15px 20px;border-bottom:1px solid var(--line-2);display:flex;align-items:center;gap:9px}
.hd h3{margin:0;font-size:13.5px;font-weight:700}
.hd .n{width:19px;height:19px;border-radius:5px;background:var(--ink);color:#fff;font:700 11px/1 inherit;
  display:grid;place-items:center;flex:none}
.hd .p{margin-left:auto;font:11px/1 var(--mono);color:var(--ink-3);background:var(--bg);padding:5px 9px;border-radius:5px}
.bd{padding:18px 20px 20px}
.sc{display:flex;flex-wrap:wrap;gap:6px}
.sc button{display:flex;align-items:center;gap:6px;padding:7px 11px 7px 8px;font:500 12.5px/1 inherit;
  border:1px solid var(--line);background:var(--sf);border-radius:18px;color:var(--ink-2);cursor:pointer;
  min-height:34px;transition:background 150ms var(--ease),border-color 150ms var(--ease),color 150ms var(--ease)}
.sc button:hover{border-color:#CFCBC4;background:var(--bg)}
.sc button[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
.dot{width:7px;height:7px;border-radius:50%;flex:none}
.dot.normal{background:var(--safe)}.dot.attack{background:var(--danger)}.dot.gap{background:var(--warn)}
.scd{font-size:12.5px;color:var(--ink-3);line-height:1.58;margin:11px 0 4px;min-height:38px}
.f{margin-top:13px}
.f>label{display:block;font-size:12px;font-weight:600;color:var(--ink-2);margin-bottom:5px}
.f .help{font-weight:400;color:var(--ink-3)}
input,select{width:100%;padding:9px 11px;border:1px solid #CFCBC4;border-radius:var(--r-s);
  font:14px/1.4 inherit;background:var(--sf);color:var(--ink);transition:border-color 150ms var(--ease)}
input.mono{font-family:var(--mono);font-size:13.5px;font-variant-numeric:tabular-nums}
input:focus,select:focus{border-color:var(--kb-d)}
select{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='11' height='7'><path d='M1 1l4.5 4.5L10 1' stroke='%237C7870' stroke-width='1.6' fill='none' stroke-linecap='round'/></svg>");
  background-repeat:no-repeat;background-position:right 11px center;padding-right:32px}
.r2{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.key{border:1px solid rgba(255,188,0,.45);background:rgba(255,188,0,.055);padding:12px 13px 13px;
  border-radius:var(--r-s);margin-top:18px}
#go{width:100%;margin-top:20px;padding:13px;border:0;border-radius:var(--r-s);cursor:pointer;min-height:44px;
  background:var(--kb);color:#231A00;font:700 14.5px/1 inherit;transition:background 150ms var(--ease)}
#go:hover{background:var(--kb-d)}
.ph{color:var(--ink-3);font-size:13px;padding:26px 4px;text-align:center;line-height:1.75}
.vd{display:flex;gap:12px;padding:15px 16px;border-radius:var(--r);margin-bottom:15px;align-items:flex-start}
.vd svg{flex:none;margin-top:1px}
.vd .t{font-size:16.5px;font-weight:700;letter-spacing:-.015em;line-height:1.35}
.vd .s{font-size:11.5px;font-family:var(--mono);opacity:.75;margin-top:3px;font-variant-numeric:tabular-nums}
.vd.BLOCK_PENDING{background:rgba(214,50,60,.09);border:1px solid rgba(214,50,60,.34);color:var(--danger)}
.vd.HOLD{background:rgba(184,116,0,.10);border:1px solid rgba(184,116,0,.32);color:var(--warn)}
.vd.UNKNOWN{background:rgba(91,97,105,.08);border:1px solid rgba(91,97,105,.28);color:var(--hold)}
.vd.PASS,.vd.NOTICE{background:rgba(15,123,95,.09);border:1px solid rgba(15,123,95,.32);color:var(--safe)}
.rs{margin:0;padding:0;list-style:none;border-top:1px solid var(--line-2)}
.rs li{display:flex;gap:9px;padding:11px 2px;border-bottom:1px solid var(--line-2);font-size:13.5px;
  color:var(--ink-2);line-height:1.6}
.rs li b{flex:none;width:5px;height:5px;border-radius:50%;background:currentColor;margin-top:8px;opacity:.4}
.src{margin-top:14px;font-size:11.5px;color:var(--ink-3);display:flex;align-items:center;gap:6px}
details{margin-top:12px}
summary{cursor:pointer;font-size:12px;color:var(--ink-3);padding:4px 0;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";color:#B4AFA6}
details[open] summary::before{content:"▾ "}
pre{background:var(--ink);color:#EDEAE4;padding:13px 15px;border-radius:var(--r-s);overflow:auto;margin:9px 0 0;
  font:11.5px/1.65 var(--mono);white-space:pre-wrap;word-break:break-all}
#doc{max-height:620px;overflow:auto;padding:16px 20px;margin:0;background:#FCFCFB;color:#3E3A34;
  font:11.5px/1.72 var(--mono);white-space:pre-wrap;font-variant-numeric:tabular-nums}

/* UPLOAD */
.up{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:14px}
@media(max-width:640px){.up{grid-template-columns:1fr}}
.up button{border:1px solid var(--line);background:var(--sf);border-radius:var(--r-s);padding:11px 13px;
  cursor:pointer;text-align:left;min-height:44px;transition:background 150ms var(--ease),border-color 150ms var(--ease)}
.up button:hover{background:var(--bg);border-color:#CFCBC4}
.up button[aria-pressed=true]{border-color:var(--kb-d);background:rgba(255,188,0,.07)}
.up b{display:block;font-size:13px;font-weight:700}
.up span{font-size:11.5px;color:var(--ink-3)}
#upBox{border:1px solid var(--line);border-radius:var(--r-s);padding:14px;background:var(--bg);margin-bottom:14px}
#upBox[hidden]{display:none}
textarea{width:100%;min-height:118px;padding:10px 11px;border:1px solid #CFCBC4;border-radius:var(--r-s);
  font:12px/1.6 var(--mono);background:var(--sf);color:var(--ink);resize:vertical;
  transition:border-color 150ms var(--ease)}
textarea:focus{outline:2px solid var(--kb-d);outline-offset:2px;border-color:var(--kb-d)}
.uprow{display:flex;gap:9px;align-items:center;margin-top:10px;flex-wrap:wrap}
.uprow .btn-p{min-height:38px;padding:0 16px;font-size:13.5px}
.fx{font-size:12px;color:var(--ink-3);cursor:pointer;text-decoration:underline;
  text-underline-offset:3px;background:0;border:0;padding:6px 0}
.dstat{display:flex;gap:9px;align-items:flex-start;padding:11px 13px;border:1px solid var(--line);
  border-radius:var(--r-s);font-size:12.5px;line-height:1.6;margin-bottom:14px}
.dstat.up-on{border-color:rgba(15,123,95,.34);background:rgba(15,123,95,.06)}
.dstat .nm{font-weight:700;font-size:13px}
.dstat .rm{margin-left:auto;flex:none}
.fgrid{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin-top:8px;font-size:12px}
.fgrid dt{color:var(--ink-3);white-space:nowrap}
.fgrid dd{margin:0;font-family:var(--mono);font-size:11.5px;word-break:break-all}
.fgrid dd.miss{color:var(--warn)}

/* 결과 카드 — 전폭 · 높이 제한 · 판정 배너는 스크롤해도 보이게 고정 */
#outWrap{max-height:600px;overflow-y:auto;overscroll-behavior:contain;padding-top:0}
#outWrap::-webkit-scrollbar{width:10px}
#outWrap::-webkit-scrollbar-thumb{background:#D8D4CD;border-radius:9px;border:3px solid var(--sf)}
#outWrap::-webkit-scrollbar-thumb:hover{background:#C5C0B8}
.res .vd{position:sticky;top:0;z-index:2;margin-top:18px}
/* 결과가 전폭이므로 근거 표는 2단으로 — 세로 스크롤을 줄인다 */
@media(min-width:1000px){
  .aud .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}
}
#doc{max-height:none}
.card>#doc{border-top:0}

/* AUDIT — HITL 검증 */
.aud{margin-top:16px;border-top:1px solid var(--line);padding-top:16px}
.aud h4{margin:0 0 4px;font-size:13px;font-weight:700;display:flex;align-items:center;gap:7px}
.aud .lead{font-size:12px;color:var(--ink-3);line-height:1.6;margin:0 0 13px}
.chain{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-bottom:15px;
  font-size:11px;color:var(--ink-3)}
.chain i{font-style:normal;background:var(--bg);border:1px solid var(--line);border-radius:12px;
  padding:4px 9px;white-space:nowrap}
.chain u{text-decoration:none;color:#B4AFA6}
.astep{margin-bottom:15px}
.astep>b{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;color:var(--ink-3);
  letter-spacing:.03em;margin-bottom:7px}
.astep>b em{font-style:normal;width:17px;height:17px;border-radius:4px;background:var(--ink);color:#fff;
  font-size:10px;display:grid;place-items:center;flex:none}
.at{width:100%;border-collapse:collapse;font-size:12px;border:1px solid var(--line);border-radius:7px;
  overflow:hidden;table-layout:fixed}
.at th{background:var(--bg);text-align:left;padding:7px 10px;font-size:10.5px;font-weight:700;
  color:var(--ink-3);border-bottom:1px solid var(--line)}
.at td{padding:8px 10px;border-bottom:1px solid var(--line-2);vertical-align:top;line-height:1.55;
  word-break:break-word}
.at tr:last-child td{border-bottom:0}
.at .v{font-family:var(--mono);font-size:11.5px;font-variant-numeric:tabular-nums}
.at .ev{font-family:var(--mono);font-size:10.5px;color:var(--ink-2);background:rgba(15,123,95,.06);
  border:1px solid rgba(15,123,95,.22);border-radius:4px;padding:4px 6px;display:inline-block}
.at .no{color:var(--warn);font-size:11px}
.at tr.hit td{background:rgba(214,50,60,.055)}
.at tr.miss td{color:#A9A49B}
.at tr.mrule td{background:rgba(255,188,0,.10);font-weight:600}
.sev{display:inline-block;font:700 9.5px/1 var(--mono);padding:3px 5px;border-radius:3px;letter-spacing:.03em}
.sev.HIGH{background:rgba(214,50,60,.13);color:var(--danger)}
.sev.MEDIUM{background:rgba(184,116,0,.14);color:var(--warn)}
.sev.LOW,.sev.NOTICE{background:rgba(91,97,105,.11);color:var(--hold)}
.sev.NONE{background:var(--line-2);color:#A9A49B}
.vfy{display:flex;gap:8px;align-items:flex-start;padding:10px 12px;border:1px solid rgba(15,123,95,.3);
  background:rgba(15,123,95,.06);border-radius:7px;font-size:11.5px;line-height:1.62;color:var(--ink-2);
  margin-bottom:14px}
.vfy b{color:var(--safe)}
.hitl{padding:11px 13px;border:1px solid var(--line);border-radius:7px;background:var(--bg);
  font-size:11.5px;line-height:1.66;color:var(--ink-2);margin-top:4px}
.hitl b{display:block;font-size:12px;color:var(--ink);margin-bottom:5px}
.hitl ol{margin:0;padding-left:17px}
.hitl li{margin:3px 0}

/* SETTINGS */
.ov{position:fixed;inset:0;background:rgba(28,26,22,.45);z-index:60;display:none;
  align-items:flex-start;justify-content:center;padding:70px 20px 20px;overflow:auto}
.ov.open{display:flex}
.md{background:var(--sf);border:1px solid var(--line);border-radius:12px;max-width:560px;width:100%}
.md .hd h3{font-size:15px}
.md .bd{padding:20px}
.mrow{display:flex;gap:9px;align-items:flex-start;padding:11px 13px;border:1px solid var(--line);
  border-radius:var(--r-s);background:var(--bg);font-size:12.5px;color:var(--ink-2);line-height:1.64;margin-bottom:16px}
.st{display:flex;align-items:center;gap:10px;padding:12px 14px;border:1px solid var(--line);
  border-radius:var(--r-s);margin-bottom:16px}
.st .d{width:8px;height:8px;border-radius:50%;background:#B9BDC3;flex:none}
.st.on .d{background:var(--safe)}
.st .txt b{display:block;font-size:13.5px}
.st .txt span{color:var(--ink-3);font-size:12px;font-family:var(--mono)}
.st .rm{margin-left:auto}
.mact{display:flex;gap:9px;margin-top:16px}
.mact .btn-p{flex:1;justify-content:center}
.mwarn{margin-top:15px;font-size:11.5px;color:var(--ink-3);line-height:1.72;
  border-top:1px solid var(--line-2);padding-top:13px}
.err{color:var(--danger);font-size:12.5px;margin-top:9px;min-height:18px}
.foot{padding:34px 0 46px;font-size:12px;color:var(--ink-3);line-height:1.85;text-align:center}
</style>

<header class=gnb><div class=in>
  <div class=mk><svg width=17 height=17 viewBox="0 0 20 20" fill=none>
    <path d="M10 1.7 3.2 4.3v5.1c0 4.2 2.8 7.6 6.8 9 4-1.4 6.8-4.8 6.8-9V4.3L10 1.7Z"
      stroke="#231A00" stroke-width=1.7 stroke-linejoin=round/>
    <path d="m7.1 9.9 2.1 2.1 4-4.2" stroke="#231A00" stroke-width=1.7 stroke-linecap=round stroke-linejoin=round/></svg></div>
  <div class=bn>KB Payee Guard</div>
  <nav>
    <a href="#problem">문제</a><a href="#how">동작 방식</a>
    <a href="#perf">성능</a><a href="#demo">직접 해보기</a>
  </nav>
  <div class=rt>
    <div class=chip id=chip><span class=d></span><span id=chipT>수동 라벨</span></div>
    <button class=btn-s id=openSet>설정</button>
  </div>
</div></header>

<div class=hero><div class=in>
  <div class=eyebrow>제8회 KB A.I Challenge · 금융 자유주제</div>
  <h1>계좌번호를 검증하지 않습니다.<br>그 계좌를 알려준 <em>경로</em>를 검증합니다.</h1>
  <p class=lead>해외송금 신청 시 <b>이미 제출된 계약서</b>를 AI가 읽어, 이번 계좌 지시가
    계약이 정한 변경 절차를 따랐는지 대조하고 어긋나면 송금을 보류하는 게이트입니다.
    계좌번호는 바꿀 수 있어도, 은행이 보관 중인 3년 전 계약서의
    &ldquo;변경은 양측 서면 합의로&rdquo;는 사후에 바꿀 수 없습니다.</p>
  <div class=cta>
    <a class=btn-p href="#demo">직접 판정해 보기
      <svg width=15 height=15 viewBox="0 0 16 16" fill=none><path d="M3 8h10m-4-4 4 4-4 4"
        stroke="#231A00" stroke-width=1.8 stroke-linecap=round stroke-linejoin=round/></svg></a>
    <a class=btn-o href="#how">동작 방식 보기</a>
  </div>
</div></div>

<section id=problem class=alt><div class=in>
  <div class=sh>풀려는 문제</div>
  <h2>3년 거래한 담당자 이름으로 메일이 옵니다</h2>
  <p class=sub>&ldquo;거래 은행이 바뀌었으니 새 계좌로 보내주세요.&rdquo; 인보이스까지 첨부돼
    있습니다. 송금합니다. 3주 뒤 상대가 말합니다 — <b>&ldquo;대금이 안 들어왔는데요.&rdquo;</b></p>
  <div class=pr>
    <div class=pc><div class=n>1,600<span class=u>건</span></div>
      <h3>무역송금 사기 접수</h3>
      <p>2021~2025 상반기 국내 접수 건수 (금감원 집계 · KBS 보도).</p></div>
    <div class=pc><div class=n>대금 전액</div>
      <h3>건당 손실 규모</h3>
      <p>부분 손실이 아니라 송금액 전체가 나갑니다. 해외 계좌라 회수가 어렵습니다.</p></div>
    <div class=pc><div class=n>이름 대조</div>
      <h3>기존 제품이 보는 것</h3>
      <p>사기범이 거래처와 <b>같은 법인명으로 계좌를 열면 통과</b>합니다 — 벤더 자신이 인정합니다.</p></div>
  </div>
</div></section>

<section id=how><div class=in>
  <div class=sh>동작 방식</div>
  <h2>계약서가 정한 절차와 이번 송금을 대조합니다</h2>
  <p class=sub>계약서 §Notices·§Amendment는 체결 시점에 확정되므로, 은행이 보관 중인 원본을
    기준으로 삼는 한 사기범이 사후에 바꿀 수 없습니다. 여기서 판정 축이 나옵니다.</p>
  <div class=flow>
    <div class=fb><h4>제출된 계약서 · 2023-04-11</h4>
      <dl><dt>상대방</dt><dd>BAUER GmbH</dd>
        <dt>소재지</dt><dd>Stuttgart, DE</dd>
        <dt>결제조건</dt><dd>Irrevocable L/C</dd>
        <dt>§14 변경</dt><dd>서면 합의로만</dd></dl></div>
    <svg class=ar width=26 height=26 viewBox="0 0 26 26" fill=none><path d="M4 13h18m-6-6 6 6-6 6"
      stroke="#7C7870" stroke-width=1.7 stroke-linecap=round stroke-linejoin=round/></svg>
    <div class=fb><h4>이번 송금 신청</h4>
      <dl><dt>수취계좌</dt><dd>LT12 … 47 (LT)</dd>
        <dt>송금방식</dt><dd>T/T</dd>
        <dt>계좌 지시</dt><dd>이메일 한 통</dd>
        <dt>발신</dt><dd>bauer-gmbh.co</dd></dl></div>
  </div>
  <div class=q>&ldquo;이 계좌 지시가 계약이 정한 경로로 왔는가?&rdquo;</div>
  <p class=sub style="margin-top:26px">가장 흔한 유형은 국가도 이름도 결제조건도 그대로이고
    <b>계좌번호만</b> 바뀝니다. 그 경우 우리가 구현한 다른 신호는 전부 침묵하고 이 축만 발화합니다.</p>
  <div class=wrapx><table class=tbl>
    <tr><th style="width:25%">이미 있는 것</th><th style="width:29%">무엇을 검증하나</th><th>같은 법인명으로 계좌를 열면</th></tr>
    <tr><td>메일 보안 (Proofpoint 등)</td><td>메일 도메인·문체</td><td>도메인이 진짜라 통과. 애초에 송금을 못 막음</td></tr>
    <tr><td>벤더 계좌 검증 (Trustpair 등)</td><td>벤더 마스터 계좌 이력</td><td>변경은 감지하나 정당/사기를 못 가름</td></tr>
    <tr><td>EU VoP (2025-10 법정)</td><td>이름 ↔ 계좌</td><td>법인명으로 계좌를 열면 통과. EU 역내 유로만</td></tr>
    <tr class=us><td>KB Payee Guard</td><td>계좌 지시가 계약 절차를 따랐는가</td><td>보관 원본의 §Amendment는 사후 변경이 어려움</td></tr>
  </table></div>
</div></section>

<section id=perf class=alt><div class=in>
  <div class=sh>실측 성능</div>
  <h2>측정한 것과 모르는 것을 나눠 적습니다</h2>
  <p class=sub>실물 계약서 262건 기반. 아래는 전부 저장소에서 재현 가능하며, <b>API 키 없이</b>
    <code>python3.12 scripts/recheck_holdout.py</code> 한 줄로 다시 셀 수 있습니다.</p>
  <div class=mt>
    <div class=mc><div class=v>92.9<span class=u>%</span></div>
      <div class=k>규칙 튜닝에 안 쓴 183건에서 위조 제외 차단율 — gold 93.3%와 같은 수준</div></div>
    <div class=mc><div class=v>0.0<span class=u>%</span></div>
      <div class=k>정상 거래 하드 차단 오탐. 단 25%는 사람 승인 대기로 갑니다</div></div>
    <div class=mc><div class=v>90.0<span class=u>%</span></div>
      <div class=k>LLM 조항 추출 정확도 — 정규식은 30.0%</div></div>
    <div class=mc><div class=v>128<span class=u>건</span></div>
      <div class=k>테스트 — 외부 API 없이 1초 미만</div></div>
  </div>
  <p class=note><b>숨기지 않는 것:</b> 위 92.9%는 독립 정답 라벨 대비 정확도가 아닙니다 —
    시나리오가 추출 결과로 생성되므로 &ldquo;추출이 비지 않았을 때 규칙이 설계대로 발화하는가&rdquo;를 잽니다.
    <b>위조 수정합의서는 막지 못하고</b>(전건 미탐), <b>국문 무역계약서 성능은 측정된 적이 없습니다</b>
    (확보한 국문 49건은 당사자가 비어 있는 표준서식이라 송금 계약이 아닙니다).
    아래 데모의 다섯 번째 시나리오에서 그 사각지대를 직접 확인하실 수 있습니다.</p>
</div></section>

<section id=demo><div class=in>
  <div class=sh>직접 해보기</div>
  <h2>시나리오를 바꿔 가며 판정을 확인하세요</h2>
  <p class=sub>값은 직접 고쳐도 됩니다. 특히 <b>&ldquo;이 계좌 정보를 어디서 받으셨습니까&rdquo;</b>만
    이메일 → 수정 합의서로 바꾸면, 계좌번호가 같은데도 차단이 통과로 뒤집힙니다. 그게 판정 축입니다.</p>
  <div class=card style="margin-bottom:20px">
    <div class=hd><div class=n>0</div><h3>어떤 계약서로 판정할까요</h3>
      <div class=p id=docName>목업 계약서</div></div>
    <div class=bd>
      <div class=up>
        <button type=button id=useMock aria-pressed=true>
          <b>목업 계약서로 보기</b><span>키 없이 즉시 · BAUER GmbH ↔ 한성정밀</span></button>
        <button type=button id=useMine aria-pressed=false>
          <b>내 계약서 올리기</b><span>실제 계약서로 추출부터 판정까지</span></button>
      </div>
      <div class=dstat id=dstat><svg width=15 height=15 viewBox="0 0 16 16" fill=none style="flex:none;margin-top:2px">
          <path d="M9 1.6H4.2a1.2 1.2 0 0 0-1.2 1.2v10.4a1.2 1.2 0 0 0 1.2 1.2h7.6a1.2 1.2 0 0 0 1.2-1.2V5.6L9 1.6Z"
            stroke="#7C7870" stroke-width=1.4 stroke-linejoin=round/>
          <path d="M9 1.6v4h4" stroke="#7C7870" stroke-width=1.4 stroke-linejoin=round/></svg>
        <div id=dstatT>목업 무역계약서로 판정합니다.</div>
        <button class="btn-s rm" id=clearDoc hidden>목업으로 되돌리기</button></div>
      <div id=upBox hidden>
        <label style="display:block;font-size:12px;font-weight:600;color:var(--ink-2);margin-bottom:6px">
          계약서 전문을 붙여 넣거나 <button class=fx id=pickFile>.txt 파일 선택</button>
          <input type=file id=fileIn accept=".txt,.md,text/plain" hidden></label>
        <textarea id=docText placeholder="INTERNATIONAL SALES CONTRACT&#10;&#10;1. PARTIES ...&#10;&#10;12. NOTICES ...&#10;&#10;14. AMENDMENT ..." spellcheck=false></textarea>
        <div class=uprow>
          <button class=btn-p id=upGo>이 계약서로 판정하기</button>
          <span style="font-size:11.5px;color:var(--ink-3)">
            OpenAI 키 필요 · 1회 추출 후 캐시 · 원문은 메모리에만</span>
        </div>
        <div class=err id=upErr></div>
      </div>
    </div>
  </div>

  <div class=grid>
    <div class=card>
      <div class=hd><div class=n>1</div><h3>송금 신청 정보</h3></div>
      <div class=bd>
        <div class=sc id=sc></div><div class=scd id=scd></div>
        <div class=f><label>수취 계좌 <span class=help>IBAN</span></label><input id=account class=mono spellcheck=false></div>
        <div class="f r2">
          <div><label>BIC / SWIFT</label><input id=bic class=mono spellcheck=false></div>
          <div><label>송금 방식</label><select id=remittance_type>
            <option value=TT>T/T · 전신송금</option><option value=LC>L/C · 신용장</option>
            <option value=DP>D/P</option><option value=DA>D/A</option></select></div></div>
        <div class="f r2">
          <div><label>송금액</label><input id=amount class=mono inputmode=decimal></div>
          <div><label>통화</label><input id=currency class=mono maxlength=3></div></div>
        <div class="f key"><label>이 계좌 정보를 어디서 받으셨습니까? <span class=help>— 판정의 핵심 입력</span></label>
          <select id=source>
            <option value=CONTRACT>계약서에 기재된 계좌</option>
            <option value=AMENDMENT>양측 서명 수정합의서</option>
            <option value=EMAIL>이메일 안내</option><option value=PHONE>전화 안내</option>
            <option value=FAX>팩스</option><option value=PORTAL>거래처 포털</option>
            <option value=INVOICE>인보이스 기재</option></select></div>
        <div class="f r2">
          <div><label>지시가 온 주소·번호</label><input id=channel_detail class=mono placeholder="ap@bauer-gmbh.co" spellcheck=false></div>
          <div><label>메일 발신자</label><input id=sender class=mono placeholder="ap@bauer-gmbh.co" spellcheck=false></div></div>
        <div class=f><label>메일 스레드 <span class=help>In-Reply-To — 비우면 새 메일</span></label>
          <input id=in_reply_to class=mono spellcheck=false></div>
        <button id=go>송금 심사 실행</button>
      </div>
    </div>
    <div class=card>
      <div class=hd><div class=n>2</div><h3>게이트가 대조한 계약서</h3>
        <div class=p id=docPath>data/demo/mock_contract.txt</div></div>
      <pre id=doc>불러오는 중…</pre>
    </div>
  </div>

  <div class="card res" style="margin-top:20px">
    <div class=hd><div class=n>3</div><h3>심사 결과</h3>
      <div class=p id=resHint>왼쪽 폼을 채우고 실행하세요</div></div>
    <div class=bd id=outWrap><div id=out><div class=ph>시나리오를 고르고
      <b>송금 심사 실행</b>을 누르면 판정과 근거 전 과정이 여기에 표시됩니다.</div></div></div>
  </div>
</div></section>

<div class=ov id=ov role=dialog aria-modal=true aria-labelledby=setT>
  <div class=md>
    <div class=hd><h3 id=setT>설정 · OpenAI API 키</h3>
      <button class=btn-s id=closeSet style="margin-left:auto">닫기</button></div>
    <div class=bd>
      <div class=mrow><svg width=15 height=15 viewBox="0 0 16 16" fill=none style="flex:none;margin-top:2px">
        <circle cx=8 cy=8 r=6.6 stroke="#8A5600" stroke-width=1.5/>
        <path d="M8 4.6v4.2" stroke="#8A5600" stroke-width=1.7 stroke-linecap=round/>
        <circle cx=8 cy=11.3 r=.95 fill="#8A5600"/></svg>
        <div>키는 이 <b>서버 프로세스 메모리에만</b> 보관됩니다 — 파일·로그·응답 어디에도 원문을 쓰지
          않고, 서버를 끄면 사라집니다. 브라우저에도 저장하지 않습니다.
          <b>키 없이도 사이트는 전부 동작합니다</b>(계약서 사실을 사람이 옮겨 적은 값으로 대체).</div></div>
      <div class=st id=st><span class=d></span>
        <div class=txt><b id=stT>키 없음</b><span id=stS>수동 라벨로 동작 중</span></div>
        <button class="btn-s rm" id=clearKey hidden>지우기</button></div>
      <div class=f><label>API 키 <span class=help>platform.openai.com/api-keys 에서 발급</span></label>
        <input id=keyIn class=mono type=password placeholder="sk-..." autocomplete=off spellcheck=false></div>
      <div class=err id=keyErr></div>
      <div class=mact><button class=btn-p id=saveKey>저장하고 LLM 추출 사용</button></div>
      <div class=mwarn>저장하면 다음 판정부터 계약서 원문을 OpenAI <code>gpt-4o-mini</code>에 보내
        조항을 추출합니다. 이 데모 계약서 1건 기준 호출당 <b>약 $0.0007</b>입니다.
        추출이 실패하면 자동으로 수동 라벨로 되돌아가며 화면에 그 사실을 표시합니다.</div>
    </div>
  </div>
</div>

<div class=foot>
  <b>실제 은행 서비스가 아닙니다.</b> 판정 엔진을 눌러 보는 로컬 확인용 사이트입니다 —
  인증·영속·감사원장이 없고 127.0.0.1 에만 바인딩합니다.<br>
  제8회 KB A.I Challenge 제출작 · 팀 aithor · KB국민은행과 무관하며 화면 구성은 제출작 자체 제작입니다.
</div>

<script>
const S = __SCENARIOS__;
const F = ['account','bic','amount','currency','remittance_type','source','channel_detail','sender','in_reply_to'];
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

const sc=$('sc');
Object.entries(S).forEach(([k,v],i)=>{
  const b=document.createElement('button'); b.type='button'; b.setAttribute('aria-pressed','false');
  b.innerHTML='<span class="dot '+(v.risk||'normal')+'"></span>'+v.label;
  b.onclick=()=>{[...sc.children].forEach(c=>c.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true');
    F.forEach(f=>$(f).value=v.form[f]??''); $('scd').textContent=v.desc;};
  sc.appendChild(b); if(i===0) b.click();
});

const ICON={
 BLOCK_PENDING:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke=currentColor stroke-width=1.8/><path d="M11 6.4v5.4" stroke=currentColor stroke-width=2 stroke-linecap=round/><circle cx=11 cy=15.2 r=1.15 fill=currentColor/></svg>',
 HOLD:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke=currentColor stroke-width=1.8/><path d="M11 6.2v5l3 1.9" stroke=currentColor stroke-width=1.9 stroke-linecap=round stroke-linejoin=round/></svg>',
 UNKNOWN:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke=currentColor stroke-width=1.8/><path d="M8.6 8.5a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.9.7-.9 1.3v.4" stroke=currentColor stroke-width=1.8 stroke-linecap=round/><circle cx=11 cy=15.4 r=1.05 fill=currentColor/></svg>',
 PASS:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke=currentColor stroke-width=1.8/><path d="m7.3 11.2 2.6 2.6 5-5.4" stroke=currentColor stroke-width=2 stroke-linecap=round stroke-linejoin=round/></svg>'};
ICON.NOTICE=ICON.PASS;
const KO={BLOCK_PENDING:['송금 보류','승인 없이는 진행할 수 없습니다'],
          HOLD:['송금 보류','담당자 확인이 필요합니다'],
          UNKNOWN:['판정 불가','근거가 부족해 승인 없이는 진행할 수 없습니다'],
          PASS:['이상 없음','계약이 정한 절차와 일치합니다'],
          NOTICE:['이상 없음','참고 사항이 있습니다']};

$('go').onclick=async()=>{
  const body={}; F.forEach(f=>body[f]=$(f).value);
  $('out').innerHTML='<div class=ph>심사 중…</div>';
  try{
    const d=await(await fetch('/judge',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)})).json();
    if(d.error){$('out').innerHTML='<pre>'+esc(d.error)+'\\n\\n'+esc(d.trace||'')+'</pre>';return;}
    const kv=KO[d.verdict]||[d.verdict,''];
    $('out').innerHTML='<div class="vd '+d.verdict+'">'+(ICON[d.verdict]||'')+
      '<div><div class=t>'+kv[0]+'</div><div class=s>'+d.verdict+' · 규칙 '+d.rule+' — '+kv[1]+'</div></div></div>'+
      (d.reasons.length?'<ul class=rs>'+d.reasons.map(x=>'<li><b></b><span>'+esc(x)+'</span></li>').join('')+'</ul>'
        :'<div style="font-size:13.5px;color:var(--ink-2);padding:2px">발화한 위험 신호가 없습니다.</div>')+
      '<div class=src><svg width=13 height=13 viewBox="0 0 14 14" fill=none><circle cx=7 cy=7 r=5.6 stroke="#7C7870" stroke-width=1.3/><path d="M7 4.3v3.4" stroke="#7C7870" stroke-width=1.4 stroke-linecap=round/><circle cx=7 cy=9.7 r=.8 fill="#7C7870"/></svg>계약서 사실 출처: '+esc(d.facts_origin)+'</div>'+
        renderAudit(d.audit)+
      '<details><summary>원시 JSON (신호 · 계약서 사실)</summary><pre>'+
        esc(JSON.stringify({신호:d.signals,계약서_사실:d.facts},null,1))+'</pre></details>';
    $('resHint').textContent = d.verdict+' · 규칙 '+d.rule;
    $('outWrap').scrollTop = 0;
    // 결과 카드가 화면 밖이면 부드럽게 이동 — 아래로 내렸으므로 안 보일 수 있다
    const rc=document.querySelector('.res');
    if(rc.getBoundingClientRect().top > window.innerHeight - 160)
      rc.scrollIntoView({behavior:'smooth',block:'start'});
    refreshKey();
  }catch(e){$('out').innerHTML='<pre>요청 실패: '+esc(String(e))+'</pre>';}
};

const ov=$('ov');
const closeSet=()=>{ov.classList.remove('open');$('keyIn').value='';$('keyErr').textContent='';};
$('openSet').onclick=()=>{ov.classList.add('open');$('keyIn').focus();};
$('closeSet').onclick=closeSet;
ov.onclick=e=>{if(e.target===ov)closeSet();};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&ov.classList.contains('open'))closeSet();});

/* 감사 로그 — HITL 이 할루시네이션을 직접 잡을 수 있게 전 단계를 편다.
   금융에서 "AI 가 그렇게 판단했다" 는 근거가 아니다. 사람이 한 칸씩 되짚어야 한다. */
function renderAudit(a){
  if(!a) return '';
  const chain='<div class=chain>'+a.chain.map((c,i)=>
    (i?'<u>&rsaquo;</u>':'')+'<i>'+esc(c)+'</i>').join('')+'</div>';

  const inRows=Object.entries(a.input).map(([k,v])=>
    '<tr><td style="width:38%">'+esc(k)+'</td><td class=v>'+esc(v??'(없음)')+'</td></tr>').join('');

  const exRows=a.extracted.map(e=>{
    const val=e.value===null||e.value===undefined||e.value===''||(Array.isArray(e.value)&&!e.value.length)
      ? '<span class=no>추출 안 됨</span>' : '<span class=v>'+esc(Array.isArray(e.value)?e.value.join(', '):e.value)+'</span>';
    const ev=e.evidence
      ? '<span class=ev>'+esc(e.evidence.length>150?e.evidence.slice(0,150)+'…':e.evidence)+'</span>'
      : '<span class=no>근거 구간 없음 — 이 값은 판정에 쓰지 마세요</span>';
    return '<tr><td style="width:24%">'+esc(e.label)+'</td><td style="width:26%">'+val+'</td><td>'+ev+'</td></tr>';
  }).join('');

  const sg=[...a.signals].sort((x,y)=>(y.fired-x.fired));
  const sgRows=sg.map(x=>
    '<tr class="'+(x.fired?'hit':'miss')+'"><td style="width:9%"><span class=v>'+esc(x.id)+'</span></td>'+
    '<td style="width:11%"><span class="sev '+esc(x.severity)+'">'+esc(x.fired?x.severity:'침묵')+'</span></td>'+
    '<td>'+esc(x.what)+(x.detail?'<br><span class=v style="color:var(--ink-3)">'+esc(x.detail)+'</span>':'')+
    (x.evidence?'<br><span class=ev style="margin-top:4px">'+esc(String(x.evidence).slice(0,150))+'</span>':'')+
    '</td></tr>').join('');

  const rlRows=a.rules.map(r=>
    '<tr class="'+(r.matched?'mrule':'')+'"><td style="width:9%"><span class=v>'+esc(r.id)+'</span></td>'+
    '<td style="width:16%">'+esc(r.verdict)+'</td><td>'+esc(r.cond)+
    (r.matched?' <b style="color:var(--warn)">← 이 규칙이 적중</b>':'')+'</td></tr>').join('');

  const sc=a.span_check;
  return '<div class=aud>'+
    '<h4><svg width=15 height=15 viewBox="0 0 16 16" fill=none><path d="M8 1.6 2.6 3.7v4.1c0 3.3 2.2 6 5.4 7.2 3.2-1.2 5.4-3.9 5.4-7.2V3.7L8 1.6Z" stroke="currentColor" stroke-width=1.4 stroke-linejoin=round/></svg>'+
      '판정 근거 전 과정 <span style="font-weight:400;color:var(--ink-3);font-size:11.5px">— 사람이 직접 검증하는 영역</span></h4>'+
    '<p class=lead>AI 가 만든 값과 규칙이 만든 값을 <b>분리해서</b> 보여줍니다. '+
      '아래 <b>근거 구간</b>을 계약서 원문(③번 카드)에서 찾아 눈으로 대조하시면, '+
      'AI 가 지어낸 값인지 실제로 계약서에 있는 문장인지 확인할 수 있습니다.</p>'+
    chain+
    '<div class=vfy><svg width=14 height=14 viewBox="0 0 16 16" fill=none style="flex:none;margin-top:2px">'+
      '<circle cx=8 cy=8 r=6.4 stroke="#0B5F49" stroke-width=1.4/><path d="m5.4 8.2 1.9 1.9 3.6-3.9" stroke="#0B5F49" stroke-width=1.6 stroke-linecap=round stroke-linejoin=round/></svg>'+
      '<div><b>근거 구간 '+sc.with_evidence+'/'+sc.total+' 확보.</b> '+esc(sc.note)+'</div></div>'+

    '<div class=cols>'+
      '<div class=astep><b><em>1</em>사람이 입력한 값 <span style="font-weight:400">— AI 가 만들지 않았습니다</span></b>'+
        '<table class=at>'+inRows+'</table></div>'+
      '<div class=astep><b><em>3</em>신호 산출 <span style="font-weight:400">— 규칙 코드가 계산. LLM 관여 없음</span></b>'+
        '<table class=at><tr><th>ID</th><th>강도</th><th>무엇을 보는가 · 실제 값</th></tr>'+sgRows+'</table></div>'+
    '</div>'+

    '<div class=astep><b><em>2</em>AI 가 계약서에서 뽑은 사실 <span style="font-weight:400">— 근거 구간을 오른쪽 계약서 원문에서 찾아 대조하세요</span></b>'+
      '<table class=at><tr><th style="width:20%">항목</th><th style="width:24%">추출값</th><th>계약서 원문 근거 (LLM 이 복사한 구간)</th></tr>'+exRows+'</table></div>'+

    '<div class=astep><b><em>4</em>규칙 테이블 <span style="font-weight:400">— 위에서부터 first-match. 왜 다른 규칙이 아닌지도 보입니다</span></b>'+
      '<table class=at><tr><th style="width:8%">규칙</th><th style="width:14%">등급</th><th>발화 조건</th></tr>'+rlRows+'</table></div>'+

    '<div class=hitl><b>담당자 확인 순서</b><ol>'+
      '<li>②의 <b>근거 구간</b>을 계약서 원문에서 찾습니다 — 없으면 AI 가 지어낸 값입니다.</li>'+
      '<li>③에서 발화한 신호의 <b>실제 값</b>이 ①·②와 맞는지 봅니다.</li>'+
      '<li>④에서 적중 규칙 <b>위쪽</b> 규칙들이 왜 발화 안 했는지 확인합니다.</li>'+
      '<li>어긋나는 칸이 하나라도 있으면 <b>승인하지 마시고</b> 원본 서류로 확인하세요.</li>'+
    '</ol></div></div>';
}

async function refreshKey(){
  try{
    const s=await(await fetch('/settings/key')).json();
    $('chip').className='chip'+(s.present?' on':''); $('chipT').textContent=s.mode;
    $('st').className='st'+(s.present?' on':'');
    $('stT').textContent=s.present?'키 등록됨':'키 없음';
    $('stS').textContent=s.present?(s.masked+' · '+(s.source==='session'?'설정에서 입력':'환경변수'))
                                  :'수동 라벨로 동작 중';
    $('clearKey').hidden=!(s.present&&s.source==='session');
  }catch(e){}
}
$('saveKey').onclick=async()=>{
  const k=$('keyIn').value.trim(); $('keyErr').textContent='';
  if(!k){$('keyErr').textContent='키를 입력하세요.';return;}
  const r=await(await fetch('/settings/key',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key:k})})).json();
  if(r.error){$('keyErr').textContent=r.error;return;}
  $('keyIn').value=''; await refreshKey(); closeSet();
};
$('clearKey').onclick=async()=>{await fetch('/settings/key',{method:'DELETE'});await refreshKey();};

/* 계약서 업로드 */
const upBox=$('upBox');
function setTab(mine){
  $('useMock').setAttribute('aria-pressed', String(!mine));
  $('useMine').setAttribute('aria-pressed', String(mine));
  upBox.hidden=!mine;
}
$('useMock').onclick=()=>setTab(false);
$('useMine').onclick=()=>{setTab(true);$('docText').focus();};
$('pickFile').onclick=e=>{e.preventDefault();$('fileIn').click();};
$('fileIn').onchange=e=>{
  const f=e.target.files[0]; if(!f) return;
  const r=new FileReader();
  r.onload=()=>{$('docText').value=r.result; $('docText').dataset.name=f.name;};
  r.readAsText(f,'utf-8');
};

async function loadDoc(){
  try{
    const d=await(await fetch('/doc')).json();
    $('docName').textContent = d.loaded ? d.name : '목업 계약서';
    $('docPath').textContent = d.loaded ? d.name : 'data/demo/mock_contract.txt';
    $('dstat').className='dstat'+(d.loaded?' up-on':'');
    $('clearDoc').hidden=!d.loaded;
    if(d.loaded){
      const f=d.facts||{};
      const row=(k,v)=>'<dt>'+k+'</dt><dd'+(v?'':' class=miss')+'>'+esc(v??'추출 실패 — 판정이 UNKNOWN 이 됩니다')+'</dd>';
      $('dstatT').innerHTML='<span class=nm>'+esc(d.name)+'</span>'+
        '<span style="color:var(--ink-3)">'+d.chars.toLocaleString()+'자 · 추출된 사실로 판정합니다</span>'+
        '<dl class=fgrid>'+row('상대방',f['상대방'])+row('소재국',f['소재국'])+
        row('결제조건',f['결제조건'])+row('변경에 서면 요구',
          f['변경에 서면 요구']===true?'예 (§Amendment 있음)':(f['변경에 서면 요구']===false?'아니오':null))+'</dl>';
      setTab(true);
    }else{
      $('dstatT').textContent='목업 무역계약서로 판정합니다. 내 계약서를 올리면 그것으로 바뀝니다.';
    }
  }catch(e){}
  fetch('/doc/text').then(r=>r.text()).then(t=>$('doc').textContent=t);
}

$('upGo').onclick=async()=>{
  const text=$('docText').value.trim(); $('upErr').textContent='';
  if(text.length<200){$('upErr').textContent='계약서 전문을 붙여 넣으세요 (200자 이상).';return;}
  const btn=$('upGo'); btn.disabled=true; btn.textContent='추출 중… (10~20초)';
  try{
    const r=await(await fetch('/doc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text,name:$('docText').dataset.name||'업로드한 계약서'})})).json();
    if(r.error){$('upErr').textContent=r.error;return;}
    await loadDoc();
    $('out').innerHTML='<div class=ph>계약서가 바뀌었습니다.<br><b>송금 심사 실행</b>을 다시 눌러 주세요.</div>';
  }catch(e){$('upErr').textContent='업로드 실패: '+String(e);}
  finally{btn.disabled=false; btn.textContent='이 계약서로 판정하기';}
};
$('clearDoc').onclick=async()=>{
  await fetch('/doc',{method:'DELETE'}); $('docText').value=''; delete $('docText').dataset.name;
  setTab(false); await loadDoc();
};

refreshKey();
loadDoc();
</script>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _doc_status(self) -> dict:
        with _doc_lock:
            if not _session_doc:
                return {"loaded": False, "source": "mock",
                        "name": "목업 무역계약서 (BAUER GmbH ↔ 한성정밀)"}
            d = _session_doc
            f = d["facts"]
            return {"loaded": True, "source": "upload", "name": d["name"],
                    "chars": len(d["text"]),
                    "facts": {"상대방": f.counterparty_name, "소재국": f.counterparty_country,
                              "결제조건": f.payment_terms.value if f.payment_terms else None,
                              "통지 경로": f.notice_channel_types,
                              "변경에 서면 요구": f.amendment_clause_requires_written,
                              "§Amendment 조항": (f.amendment_clause or "")[:200] or None}}

    def do_GET(self) -> None:                                        # noqa: N802
        if self.path in ("/", "/index.html"):
            page = PAGE.replace("__SCENARIOS__", json.dumps(SCENARIOS, ensure_ascii=False))
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/contract":
            self._send(200, CONTRACT_PATH.read_bytes(), "text/plain; charset=utf-8")
        elif self.path == "/settings/key":
            self._json(key_status())                       # 🔴 마스킹된 값만 나간다
        elif self.path == "/doc":
            self._json(self._doc_status())
        elif self.path == "/doc/text":
            with _doc_lock:
                body = (_session_doc["text"] if _session_doc
                        else CONTRACT_PATH.read_text(encoding="utf-8")).encode("utf-8")
            self._send(200, body, "text/plain; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:                                       # noqa: N802
        global _session_key
        if self.path == "/settings/key":
            try:
                k = (self._body().get("key") or "").strip()
            except Exception:                                        # noqa: BLE001
                self._json({"error": "요청을 읽지 못했습니다."}, 400)
                return
            if not k.startswith("sk-") or len(k) < 20:
                self._json({"error": "키 형식이 올바르지 않습니다 — sk- 로 시작해야 합니다."}, 400)
                return
            with _key_lock:
                _session_key = k
            print("  API 키 등록됨 (메모리 보관 · 원문 미기록)")
            self._json(key_status())
            return

        if self.path == "/doc":
            global _session_doc
            try:
                b = self._body()
                text = (b.get("text") or "").strip()
                name = (b.get("name") or "업로드한 계약서").strip()[:80]
            except Exception:                                        # noqa: BLE001
                self._json({"error": "요청을 읽지 못했습니다."}, 400); return
            if len(text) < 200:
                self._json({"error": "계약서가 너무 짧습니다 (200자 이상 필요). "
                                     "PDF 라면 텍스트를 복사해 붙여 넣으세요."}, 400); return
            if len(text.encode("utf-8")) > MAX_DOC_BYTES:
                self._json({"error": f"파일이 너무 큽니다 (최대 {MAX_DOC_BYTES // 1000}KB)."}, 400)
                return
            try:
                facts, origin = extract_facts(text)
            except Exception as exc:                                 # noqa: BLE001
                # 🔴 키가 섞여 나갈 수 있으므로 RuntimeError(우리가 만든 안내문)만 그대로,
                #    그 외 예외는 타입 이름만 노출한다.
                msg = str(exc) if isinstance(exc, RuntimeError) else \
                      f"추출에 실패했습니다 ({type(exc).__name__})."
                self._json({"error": msg}, 400); return
            with _doc_lock:
                _session_doc = {"name": name, "text": text, "facts": facts, "origin": origin}
            print(f"  계약서 업로드됨: {name} ({len(text):,}자, 메모리 보관)")
            self._json(self._doc_status()); return

        if self.path != "/judge":
            self._send(404, b"not found", "text/plain")
            return
        try:
            result = judge(self._body())
        except Exception as exc:                                     # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
        self._json(result)

    def do_DELETE(self) -> None:                                     # noqa: N802
        global _session_key, _session_doc
        if self.path == "/doc":
            with _doc_lock:
                _session_doc = None
            self._json(self._doc_status()); return
        if self.path == "/settings/key":
            with _key_lock:
                _session_key = None
            self._json(key_status())
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, fmt: str, *args) -> None:                  # 요청 로그 억제
        pass


def main() -> None:
    if not CONTRACT_PATH.exists():
        sys.exit(f"목업 계약서가 없습니다: {CONTRACT_PATH}")
    st = key_status()
    mode = "환경변수에서 감지됨 → LLM 추출" if st["present"] else "없음 → 수동 라벨 (화면 설정에서 입력 가능)"
    print("\n  KB Payee Guard — 로컬 데모 사이트")
    print("  ─────────────────────────────────────────────")
    print(f"  주소     http://127.0.0.1:{PORT}")
    print(f"  계약서   {CONTRACT_PATH.relative_to(ROOT)}")
    print(f"  API 키   {mode}")
    print("\n  중지: Ctrl+C\n")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("  종료했습니다.")


if __name__ == "__main__":
    main()
