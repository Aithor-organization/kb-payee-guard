#!/usr/bin/env python3.12
"""브라우저에서 게이트를 직접 눌러 보는 **로컬 데모 서버** (stdlib only).

    python3.12 scripts/demo_server.py      →  http://127.0.0.1:8765

## 이게 무엇이고 무엇이 아닌가

🔴 **은행 연동도, 프로덕션 REST API 도 아니다.** 판정 엔진(`rules.evaluate`)을 손으로
눌러 볼 수 있게 감싼 **로컬 확인용 화면**이다. 인증·영속·감사원장·동시성 처리가 없고
127.0.0.1 에만 바인딩한다. README 의 "REST API·송금 신청 화면 미구현(P7)" 은 그대로다.

## 왜 stdlib 만 쓰나

코어가 `pip install` 없이 도는 것이 이 저장소의 전제다(README §직접 돌려보기).
데모 하나 때문에 Flask 를 끌어오면 그 전제가 깨진다. `http.server` 로 충분하다.

## 계약서는 어디서 오나

`data/demo/mock_contract.txt` (목업 무역계약서). **API 키가 있으면** 이 원문을 LLM 추출기에
넣어 사실을 뽑고, **없으면** 같은 계약서를 사람이 읽고 옮겨 적은 값(`_FALLBACK_FACTS`)을 쓴다.
→ 키가 없어도 화면은 완전히 동작하며, 어느 경로를 썼는지 응답에 표시한다.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
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


def load_facts() -> tuple[ContractFacts, str]:
    """계약서 → 사실. 키가 있으면 LLM 추출, 없으면 수동 라벨."""
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from kb_payee_guard.llm_extract import LLMExtractor
            return LLMExtractor().extract(text), "LLM 추출 (gpt-4o-mini)"
        except Exception as exc:                                   # noqa: BLE001
            print(f"  ⚠️  LLM 추출 실패 → 수동 라벨로 대체: {type(exc).__name__}: {exc}")
    return ContractFacts(**_FALLBACK_FACTS), "수동 라벨 (키 없음 — 추출기 미사용)"


# ── 시나리오 프리셋 ────────────────────────────────────────────────────────────
#   화면의 "시나리오" 버튼이 폼을 이 값으로 채운다. 직접 고쳐서 눌러도 된다.
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
        "label": "같은 나라, 계좌만 교체 (최빈 BEC)", "risk": "attack",
        "desc": "국가·이름·결제조건 전부 그대로. 이메일 한 통으로 계좌만 바꿔 달라고 한다.",
        "form": dict(account="DE12500105170648489890", bic="INGDDEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "bec_hop": {
        "label": "제3국 계좌 + 결제조건 변경", "risk": "attack",
        "desc": "독일 회사인데 리투아니아 계좌, L/C 였는데 T/T 로. 금감원 지시 항목에 해당.",
        "form": dict(account="LT121000011101001047", bic="REVOLT21",
                     amount="184500", currency="EUR", remittance_type="TT",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "forged": {
        "label": "위조 수정합의서 (알려진 미탐)", "risk": "gap",
        "desc": "가짜 수정합의서를 만들어 절차를 지킨 것처럼 꾸민다. 이 게이트는 못 막는다.",
        "form": dict(account="DE12500105170648489890", bic="INGDDEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="AMENDMENT", channel_detail="", sender="", in_reply_to=""),
    },
}


def judge(form: dict) -> dict:
    """폼 입력 → 판정. 실패해도 500 대신 사유를 돌려준다."""
    facts, origin = load_facts()
    instr_src = InstructionSource[form.get("source", "EMAIL")]
    req = RemittanceRequest(
        case_id=form.get("case_id") or "DEMO-0001",
        payee_name=facts.counterparty_name or "BAUER Maschinenbau GmbH",
        new_account=Account(number=form["account"].replace(" ", ""), bic=form.get("bic") or None),
        amount=Money(float(form.get("amount") or 0), form.get("currency") or "EUR"),
        remittance_type=PaymentTerms[form.get("remittance_type", "TT")],
        account_instruction=AccountInstruction(
            source=instr_src, channel_detail=form.get("channel_detail") or None),
        has_contract=True,
        change_request_sender=form.get("sender") or None,
        change_request_in_reply_to=form.get("in_reply_to") or None,
    )
    d = rules.evaluate(facts, req)
    return {
        "verdict": d.verdict.value,
        "rule": d.rule_id,
        "reasons": list(d.reasons()),
        "signals": [f"{h.signal_id} {h.name} ({h.severity.name})" for h in d.hits],
        "facts_origin": origin,
        "facts": {
            "상대방": facts.counterparty_name, "소재국": facts.counterparty_country,
            "결제조건": facts.payment_terms.value if facts.payment_terms else None,
            "통지 경로": facts.notice_channel_types,
            "변경에 서면 요구": facts.amendment_clause_requires_written,
        },
    }


# ── 화면 ──────────────────────────────────────────────────────────────────────
# ── 화면 ──────────────────────────────────────────────────────────────────────
#
#  KB 노란색(#FFBC00)은 **강조 3곳에만** — 상단 마크 · 주 버튼 · 핵심 입력의 좌측 바.
#  판정 결과에는 절대 쓰지 않는다: 브랜드색과 상태색이 섞이면 위험 신호가 죽는다.
#  🔴 아이콘은 전부 **인라인 SVG**다 — 이모지는 OS 마다 모양이 달라 금융 UI 에서 신뢰를 깎는다.
#  외부 리소스 0(폰트·아이콘·스크립트 전부 인라인) — 오프라인·폐쇄망에서도 그대로 뜬다.
PAGE = """<!doctype html><html lang=ko><meta charset=utf-8>
<title>KB Payee Guard — 해외송금 수취인 검증</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
/* ── 토큰 ────────────────────────────────────────────────────────────────────
   KB 노란색은 **강조에만** 쓴다 — 상단 바 · 주 버튼 · 활성 탭 3곳.
   판정 결과에는 절대 쓰지 않는다(브랜드색과 상태색이 섞이면 위험 신호가 죽는다).   */
:root{
  --kb-yellow:#FFBC00; --kb-yellow-d:#F0A800; --kb-gray:#60584C;
  --ink:#1C1A16; --ink-2:#4C4941; --ink-3:#7C7870;
  --bg:#F5F4F2; --surface:#FFF; --line:#E5E2DD; --line-2:#F0EEEA;
  --danger:#D6323C; --danger-bg:#FDF2F3; --danger-line:#F3C9CD;
  --warn:#B87400;   --warn-bg:#FFF8EC;   --warn-line:#F2DDB4;
  --hold:#5B6169;   --hold-bg:#F4F5F7;   --hold-line:#DDE1E6;
  --safe:#0F7B5F;   --safe-bg:#F0F8F5;   --safe-line:#BFE0D4;
  --r:10px; --r-s:7px; --ease:cubic-bezier(.23,1,.32,1);
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  -webkit-font-smoothing:antialiased}

/* ── 상단 바 ── */
.gnb{background:var(--surface);border-bottom:1px solid var(--line)}
.gnb-in{max-width:1240px;margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:13px}
.mark{width:30px;height:30px;border-radius:8px;background:var(--kb-yellow);
  display:grid;place-items:center;flex:none}
.brand{font-size:16.5px;font-weight:700;letter-spacing:-.01em}
.brand span{color:var(--ink-3);font-weight:500}
.tag{margin-left:auto;font-size:11.5px;color:var(--ink-3);border:1px solid var(--line);
  padding:4px 9px;border-radius:20px;letter-spacing:.02em}

/* ── 레이아웃 ── */
.wrap{max-width:1240px;margin:0 auto;padding:24px 24px 72px}
.notice{display:flex;gap:10px;background:var(--warn-bg);border:1px solid var(--warn-line);
  border-radius:var(--r);padding:12px 15px;font-size:13px;color:#7A5200;margin-bottom:20px;line-height:1.55}
.notice b{color:#6B4700}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;align-items:start}
@media(max-width:940px){.grid{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.hd{padding:15px 20px;border-bottom:1px solid var(--line-2);display:flex;align-items:center;gap:9px}
.hd h2{margin:0;font-size:13.5px;font-weight:700;letter-spacing:-.005em}
.hd .n{width:19px;height:19px;border-radius:5px;background:var(--ink);color:#fff;font-size:11px;
  font-weight:700;display:grid;place-items:center;flex:none}
.bd{padding:18px 20px 20px}

/* ── 시나리오 탭 ── */
.sc{display:flex;flex-wrap:wrap;gap:6px}
.sc button{display:flex;align-items:center;gap:6px;padding:7px 11px 7px 8px;font:500 12.5px/1 inherit;
  border:1px solid var(--line);background:var(--surface);border-radius:18px;color:var(--ink-2);
  cursor:pointer;min-height:34px;
  transition:background 150ms var(--ease),border-color 150ms var(--ease),color 150ms var(--ease)}
.sc button:hover{border-color:#C3C8CF;background:#FAFBFC}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
.sc button[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
.sc button[aria-pressed=true] .dot{opacity:.95}
.dot{width:7px;height:7px;border-radius:50%;flex:none}
.dot.normal{background:var(--safe)} .dot.attack{background:var(--danger)} .dot.gap{background:var(--warn)}
.scd{font-size:12.5px;color:var(--ink-3);line-height:1.5;margin:11px 0 4px;min-height:38px}

/* ── 폼 ── */
.f{margin-top:13px}
.f>label{display:block;font-size:12px;font-weight:600;color:var(--ink-2);margin-bottom:5px}
.f .help{font-weight:400;color:var(--ink-3)}
input,select{width:100%;padding:9px 11px;border:1px solid #CFD4DA;border-radius:var(--r-s);
  font:14px/1.4 inherit;background:var(--surface);color:var(--ink);
  transition:border-color 150ms var(--ease)}
input.mono{font-family:var(--mono);font-size:13.5px;letter-spacing:.01em;
  font-variant-numeric:tabular-nums}
input:focus-visible,select:focus-visible,button:focus-visible{
  outline:2px solid var(--kb-yellow-d);outline-offset:2px}
input:focus,select:focus{border-color:var(--kb-yellow-d)}
select{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='11' height='7'><path d='M1 1l4.5 4.5L10 1' stroke='%23797F87' stroke-width='1.6' fill='none' stroke-linecap='round'/></svg>");
  background-repeat:no-repeat;background-position:right 11px center;padding-right:32px}
.r2{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.key{border:1px solid rgba(255,188,0,.45);background:rgba(255,188,0,.055);
  padding:12px 13px 13px;border-radius:var(--r-s);margin-top:18px}
#go{width:100%;margin-top:20px;padding:13px;border:0;border-radius:var(--r-s);cursor:pointer;
  background:var(--kb-yellow);color:#231A00;font:700 14.5px/1 inherit;letter-spacing:-.01em;
  min-height:44px;transition:background 150ms var(--ease)}
#go:hover{background:var(--kb-yellow-d)}
#go:active{transform:translateY(1px)}

/* ── 판정 ── */
.ph{color:var(--ink-3);font-size:13px;padding:26px 4px;text-align:center;line-height:1.7}
.vd{display:flex;gap:12px;padding:15px 16px;border-radius:var(--r);margin-bottom:15px;align-items:flex-start}
.vd svg{flex:none;margin-top:1px}
.vd .t{font-size:16.5px;font-weight:700;letter-spacing:-.015em;line-height:1.35}
.vd .s{font-size:11.5px;font-family:var(--mono);opacity:.75;margin-top:3px;letter-spacing:.02em;
  font-variant-numeric:tabular-nums}
.vd.BLOCK_PENDING{background:rgba(214,50,60,.09);border:1px solid rgba(214,50,60,.34);color:#A81E28}
.vd.HOLD{background:rgba(184,116,0,.10);border:1px solid rgba(184,116,0,.32);color:#8A5600}
.vd.UNKNOWN{background:rgba(91,97,105,.08);border:1px solid rgba(91,97,105,.28);color:#454B53}
.vd.PASS,.vd.NOTICE{background:rgba(15,123,95,.09);border:1px solid rgba(15,123,95,.32);color:#0B5F49}
.rs{margin:0;padding:0;list-style:none;border-top:1px solid var(--line-2)}
.rs li{display:flex;gap:9px;padding:11px 2px;border-bottom:1px solid var(--line-2);font-size:13.5px;
  color:var(--ink-2);line-height:1.55}
.rs li b{flex:none;width:5px;height:5px;border-radius:50%;background:currentColor;margin-top:8px;opacity:.4}
.src{margin-top:14px;font-size:11.5px;color:var(--ink-3);display:flex;align-items:center;gap:6px}
details{margin-top:12px}
summary{cursor:pointer;font-size:12px;color:var(--ink-3);padding:4px 0;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";color:#A9AFB7}
details[open] summary::before{content:"▾ "}
pre{background:#1B1D1F;color:#E8EAED;padding:13px 15px;border-radius:var(--r-s);overflow:auto;margin:9px 0 0;
  font:11.5px/1.65 var(--mono);white-space:pre-wrap;word-break:break-all}

/* ── 계약서 ── */
.doc-hd{display:flex;align-items:center;gap:9px;padding:15px 20px;border-bottom:1px solid var(--line-2)}
.doc-hd .p{margin-left:auto;font:11px/1 var(--mono);color:var(--ink-3);background:var(--bg);
  padding:5px 9px;border-radius:5px}
#doc{max-height:400px;overflow:auto;padding:16px 20px;margin:0;background:#FCFCFB;
  font-variant-numeric:tabular-nums;
  font:11.5px/1.72 var(--mono);white-space:pre-wrap;color:#3A3E44}
#doc::-webkit-scrollbar{width:9px} #doc::-webkit-scrollbar-thumb{background:#D5DAE0;border-radius:9px}
.foot{margin-top:22px;font-size:11.5px;color:#9AA0A8;text-align:center;line-height:1.7}
</style>

<header class=gnb><div class=gnb-in>
  <div class=mark><svg width=17 height=17 viewBox="0 0 20 20" fill="none">
    <path d="M10 1.7 3.2 4.3v5.1c0 4.2 2.8 7.6 6.8 9 4-1.4 6.8-4.8 6.8-9V4.3L10 1.7Z"
          stroke="#231A00" stroke-width="1.7" stroke-linejoin="round"/>
    <path d="m7.1 9.9 2.1 2.1 4-4.2" stroke="#231A00" stroke-width="1.7"
          stroke-linecap="round" stroke-linejoin="round"/></svg></div>
  <div class=brand>KB Payee&nbsp;Guard <span>· 해외송금 수취인 검증</span></div>
  <div class=tag>DEMO</div>
</div></header>

<div class=wrap>
  <div class=notice>
    <svg width=16 height=16 viewBox="0 0 16 16" fill=none style="flex:none;margin-top:1px">
      <circle cx=8 cy=8 r=6.6 stroke="#B87400" stroke-width=1.5/>
      <path d="M8 4.6v4.2" stroke="#B87400" stroke-width=1.7 stroke-linecap=round/>
      <circle cx=8 cy=11.3 r=.95 fill="#B87400"/></svg>
    <div><b>실제 은행 서비스가 아닙니다.</b> 판정 엔진을 손으로 눌러 보는 로컬 확인용 화면입니다 —
      인증·영속·감사원장이 없고 <code style="font-family:var(--mono);font-size:12px">127.0.0.1</code> 에만
      바인딩합니다. KB국민은행과 무관한 공모전 제출용 데모이며 화면의 색·서식은 제출작 자체 구성입니다.</div>
  </div>

  <div class=grid>
    <div class=card>
      <div class=hd><div class=n>1</div><h2>송금 신청 정보</h2></div>
      <div class=bd>
        <div class=sc id=sc></div>
        <div class=scd id=scd></div>

        <div class=f><label>수취 계좌 <span class=help>IBAN</span></label>
          <input id=account class=mono spellcheck=false></div>
        <div class="f r2">
          <div><label>BIC / SWIFT</label><input id=bic class=mono spellcheck=false></div>
          <div><label>송금 방식</label><select id=remittance_type>
            <option value=TT>T/T · 전신송금</option><option value=LC>L/C · 신용장</option>
            <option value=DP>D/P</option><option value=DA>D/A</option></select></div>
        </div>
        <div class="f r2">
          <div><label>송금액</label><input id=amount class=mono inputmode=decimal></div>
          <div><label>통화</label><input id=currency class=mono maxlength=3></div>
        </div>

        <div class="f key"><label>이 계좌 정보를 어디서 받으셨습니까?
            <span class=help>— 판정의 핵심 입력</span></label>
          <select id=source>
            <option value=CONTRACT>계약서에 기재된 계좌</option>
            <option value=AMENDMENT>양측 서명 수정합의서</option>
            <option value=EMAIL>이메일 안내</option>
            <option value=PHONE>전화 안내</option>
            <option value=FAX>팩스</option>
            <option value=PORTAL>거래처 포털</option>
            <option value=INVOICE>인보이스 기재</option>
          </select></div>

        <div class="f r2">
          <div><label>지시가 온 주소·번호</label>
            <input id=channel_detail class=mono placeholder="ap@bauer-gmbh.co" spellcheck=false></div>
          <div><label>메일 발신자</label>
            <input id=sender class=mono placeholder="ap@bauer-gmbh.co" spellcheck=false></div>
        </div>
        <div class=f><label>메일 스레드 <span class=help>In-Reply-To — 비우면 새 메일</span></label>
          <input id=in_reply_to class=mono spellcheck=false></div>

        <button id=go>송금 심사 실행</button>
      </div>
    </div>

    <div class=card>
      <div class=hd><div class=n>2</div><h2>심사 결과</h2></div>
      <div class=bd><div id=out><div class=ph>왼쪽에서 시나리오를 고르고<br><b>송금 심사 실행</b>을 누르세요.</div></div></div>
    </div>
  </div>

  <div class="card" style="margin-top:20px">
    <div class=doc-hd><div class=n style="width:19px;height:19px;border-radius:5px;background:var(--ink);color:#fff;font:700 11px/1 inherit;display:grid;place-items:center">3</div>
      <h2 style="margin:0;font-size:13.5px;font-weight:700">게이트가 대조한 계약서</h2>
      <div class=p>data/demo/mock_contract.txt</div></div>
    <pre id=doc>불러오는 중…</pre>
  </div>

  <div class=foot>제8회 KB A.I Challenge · 팀 aithor<br>
    화면의 색상·서식은 제출작 자체 구성이며 KB국민은행 공식 디자인이 아닙니다.</div>
</div>

<script>
const S = __SCENARIOS__;
const F = ['account','bic','amount','currency','remittance_type','source','channel_detail','sender','in_reply_to'];
const sc = document.getElementById('sc'), scd = document.getElementById('scd');

Object.entries(S).forEach(([k,v],i)=>{
  const b=document.createElement('button');
  b.type='button'; b.setAttribute('aria-pressed','false');
  b.innerHTML='<span class="dot '+(v.risk||'normal')+'"></span>'+v.label;
  b.onclick=()=>{
    [...sc.children].forEach(c=>c.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true');
    F.forEach(f=>document.getElementById(f).value = v.form[f] ?? '');
    scd.textContent = v.desc;
  };
  sc.appendChild(b); if(i===0) b.click();
});

const ICON = {
  BLOCK_PENDING:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke="currentColor" stroke-width=1.8/><path d="M11 6.4v5.4" stroke="currentColor" stroke-width=2 stroke-linecap=round/><circle cx=11 cy=15.2 r=1.15 fill="currentColor"/></svg>',
  HOLD:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke="currentColor" stroke-width=1.8/><path d="M11 6.2v5l3 1.9" stroke="currentColor" stroke-width=1.9 stroke-linecap=round stroke-linejoin=round/></svg>',
  UNKNOWN:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke="currentColor" stroke-width=1.8/><path d="M8.6 8.5a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.9.7-.9 1.3v.4" stroke="currentColor" stroke-width=1.8 stroke-linecap=round/><circle cx=11 cy=15.4 r=1.05 fill="currentColor"/></svg>',
  PASS:'<svg width=22 height=22 viewBox="0 0 22 22" fill=none><circle cx=11 cy=11 r=9 stroke="currentColor" stroke-width=1.8/><path d="m7.3 11.2 2.6 2.6 5-5.4" stroke="currentColor" stroke-width=2 stroke-linecap=round stroke-linejoin=round/></svg>'};
ICON.NOTICE = ICON.PASS;

const KO = {BLOCK_PENDING:['송금 보류','승인 없이는 진행할 수 없습니다'],
            HOLD:['송금 보류','담당자 확인이 필요합니다'],
            UNKNOWN:['판정 불가','근거가 부족해 승인 없이는 진행할 수 없습니다'],
            PASS:['이상 없음','계약이 정한 절차와 일치합니다'],
            NOTICE:['이상 없음','참고 사항이 있습니다']};

document.getElementById('go').onclick = async () => {
  const body={}; F.forEach(f=>body[f]=document.getElementById(f).value);
  const out=document.getElementById('out');
  out.innerHTML='<div class=ph>심사 중…</div>';
  try{
    const r=await fetch('/judge',{method:'POST',headers:{'Content-Type':'application/json'},
                                 body:JSON.stringify(body)});
    const d=await r.json();
    if(d.error){ out.innerHTML='<pre>'+esc(d.error)+'\\n\\n'+esc(d.trace||'')+'</pre>'; return; }
    const [t,s]=KO[d.verdict]||[d.verdict,''];
    out.innerHTML=
      '<div class="vd '+d.verdict+'">'+(ICON[d.verdict]||'')+
        '<div><div class=t>'+t+'</div><div class=s>'+d.verdict+' · 규칙 '+d.rule+' — '+s+'</div></div></div>'+
      (d.reasons.length
        ? '<ul class=rs>'+d.reasons.map(x=>'<li><b></b><span>'+esc(x)+'</span></li>').join('')+'</ul>'
        : '<div style="font-size:13.5px;color:var(--ink-2);padding:2px">발화한 위험 신호가 없습니다.</div>')+
      '<div class=src><svg width=13 height=13 viewBox="0 0 14 14" fill=none><circle cx=7 cy=7 r=5.6 stroke="#797F87" stroke-width=1.3/><path d="M7 4.3v3.4" stroke="#797F87" stroke-width=1.4 stroke-linecap=round/><circle cx=7 cy=9.7 r=.8 fill="#797F87"/></svg>계약서 사실 출처: '+esc(d.facts_origin)+'</div>'+
      '<details><summary>발화 신호 · 추출된 계약서 사실</summary><pre>'+
        esc(JSON.stringify({신호:d.signals,계약서_사실:d.facts},null,1))+'</pre></details>';
  }catch(e){ out.innerHTML='<pre>요청 실패: '+esc(String(e))+'</pre>'; }
};
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
fetch('/contract').then(r=>r.text()).then(t=>document.getElementById('doc').textContent=t);
</script>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:                                        # noqa: N802
        if self.path in ("/", "/index.html"):
            page = PAGE.replace("__SCENARIOS__", json.dumps(SCENARIOS, ensure_ascii=False))
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/contract":
            self._send(200, CONTRACT_PATH.read_bytes(), "text/plain; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:                                       # noqa: N802
        if self.path != "/judge":
            self._send(404, b"not found", "text/plain")
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            result = judge(json.loads(self.rfile.read(n) or b"{}"))
        except Exception as exc:                                     # noqa: BLE001
            # 데모이므로 스택을 그대로 보여 준다 — 사용자가 원인을 바로 본다.
            result = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
        self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:                  # 요청 로그 억제
        pass


def main() -> None:
    if not CONTRACT_PATH.exists():
        sys.exit(f"🔴 목업 계약서가 없습니다: {CONTRACT_PATH}")
    key = "있음 → LLM 추출 경로" if os.environ.get("OPENAI_API_KEY") else "없음 → 수동 라벨 경로"
    print(f"\n  KB Payee Guard 로컬 데모")
    print(f"  ─────────────────────────────────────────────")
    print(f"  주소     http://127.0.0.1:{PORT}")
    print(f"  계약서   {CONTRACT_PATH.relative_to(ROOT)}")
    print(f"  API 키   {key}")
    print(f"\n  중지: Ctrl+C\n")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("  종료했습니다.")


if __name__ == "__main__":
    main()
