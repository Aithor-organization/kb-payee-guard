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
        "label": "정상 — 계약서대로 송금",
        "desc": "계약서 §4 의 독일 LBBW 계좌로, 계약서가 정한 L/C 로 보낸다.",
        "form": dict(account="DE44600501010002034567", bic="SOLADEST600",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="CONTRACT", channel_detail="", sender="", in_reply_to=""),
    },
    "legit_change": {
        "label": "정상 — 적법한 계좌 변경",
        "desc": "양측이 서명한 수정합의서로 계좌를 바꿨다. 국가·결제조건은 그대로.",
        "form": dict(account="DE89370400440532013000", bic="COBADEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="AMENDMENT", channel_detail="", sender="", in_reply_to=""),
    },
    "bec_swap": {
        "label": "🔴 사기 — 같은 나라, 계좌만 교체 (최빈 BEC)",
        "desc": "국가·이름·결제조건 전부 그대로. 이메일 한 통으로 계좌만 바꿔 달라고 한다.",
        "form": dict(account="DE12500105170648489890", bic="INGDDEFF",
                     amount="184500", currency="EUR", remittance_type="LC",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "bec_hop": {
        "label": "🔴 사기 — 제3국 계좌 + 결제조건 변경",
        "desc": "독일 회사인데 리투아니아 계좌, L/C 였는데 T/T 로. 금감원 지시 항목에 해당.",
        "form": dict(account="LT121000011101001047", bic="REVOLT21",
                     amount="184500", currency="EUR", remittance_type="TT",
                     source="EMAIL", channel_detail="ap@bauer-gmbh.co",
                     sender="ap@bauer-gmbh.co", in_reply_to=""),
    },
    "forged": {
        "label": "⚠️ 사기 — 위조 수정합의서 (알려진 미탐)",
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
PAGE = """<!doctype html><html lang=ko><meta charset=utf-8>
<title>KB Payee Guard — 로컬 데모</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;
     background:#f6f7f9;color:#1a1d21}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:21px;margin:0 0 4px} .sub{color:#666;font-size:13px;margin-bottom:22px}
.warn{background:#fff8e1;border:1px solid #f0d48a;border-radius:8px;padding:10px 14px;
      font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:18px 20px}
.card h2{font-size:14px;margin:0 0 14px;color:#444;letter-spacing:.02em}
label{display:block;font-size:12px;color:#666;margin:11px 0 4px}
input,select{width:100%;padding:8px 10px;border:1px solid #ccd1d7;border-radius:6px;
             font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:#fff}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
button{cursor:pointer;font-family:inherit}
.sc{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:6px}
.sc button{padding:7px 11px;font-size:12px;border:1px solid #ccd1d7;background:#fff;
           border-radius:16px;color:#333}
.sc button:hover{border-color:#8b93a0;background:#f2f4f7}
.sc button.on{background:#1a1d21;color:#fff;border-color:#1a1d21}
#desc{font-size:12px;color:#666;min-height:34px;margin:2px 0 10px}
#go{width:100%;margin-top:18px;padding:12px;font-size:14px;font-weight:600;
    background:#1a1d21;color:#fff;border:0;border-radius:7px}
#go:hover{background:#000}
pre{background:#0f1115;color:#e6e9ef;padding:14px;border-radius:8px;overflow:auto;
    font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;margin:0}
.v{font-size:22px;font-weight:700;padding:14px 16px;border-radius:9px;margin-bottom:14px}
.v small{display:block;font-size:12px;font-weight:400;opacity:.85;margin-top:3px}
.BLOCK_PENDING{background:#fdecec;color:#b3261e;border:1px solid #f3b9b4}
.HOLD{background:#fff5e5;color:#a35b00;border:1px solid #f0cf9a}
.UNKNOWN{background:#eef0f3;color:#4a4f57;border:1px solid #d3d8de}
.PASS,.NOTICE{background:#e9f7ec;color:#166a30;border:1px solid #b3e0c0}
ul{margin:0;padding-left:19px} li{margin:5px 0;font-size:13.5px}
.meta{font-size:11.5px;color:#777;margin-top:12px;border-top:1px solid #eceef1;padding-top:9px}
details{margin-top:14px} summary{cursor:pointer;font-size:12px;color:#666}
#doc{max-height:340px;overflow:auto;background:#fbfcfd;border:1px solid #e8eaee;border-radius:7px;
     padding:12px;font:11.5px/1.6 ui-monospace,Menlo,monospace;white-space:pre-wrap;color:#333}
</style>
<div class=wrap>
<h1>KB Payee Guard — 로컬 데모</h1>
<div class=sub>계약서가 정한 계좌 변경 절차와 이번 송금을 대조합니다.</div>

<div class=warn>🔴 <b>은행 연동도 프로덕션 API도 아닙니다.</b> 판정 엔진을 손으로 눌러 보는
확인용 화면입니다 — 인증·영속·감사원장 없음, 127.0.0.1 전용.</div>

<div class=grid>
  <div class=card>
    <h2>① 시나리오를 고르거나 값을 직접 고치세요</h2>
    <div class=sc id=sc></div>
    <div id=desc></div>
    <label>수취 계좌 (IBAN)</label><input id=account>
    <div class=row>
      <div><label>BIC</label><input id=bic></div>
      <div><label>송금 방식</label><select id=remittance_type>
        <option value=TT>T/T (전신송금)</option><option value=LC>L/C (신용장)</option>
        <option value=DP>D/P</option><option value=DA>D/A</option></select></div>
    </div>
    <div class=row>
      <div><label>금액</label><input id=amount></div>
      <div><label>통화</label><input id=currency></div>
    </div>
    <label>이 계좌를 <b>어디서 받았습니까</b> (S16 의 핵심 입력)</label>
    <select id=source>
      <option value=CONTRACT>계약서에 적힌 계좌</option>
      <option value=AMENDMENT>수정 합의서</option>
      <option value=EMAIL>이메일</option>
      <option value=PHONE>전화</option>
      <option value=FAX>팩스</option>
      <option value=PORTAL>포털</option>
      <option value=INVOICE>인보이스</option>
    </select>
    <div class=row>
      <div><label>지시가 온 주소/번호</label><input id=channel_detail placeholder="ap@bauer-gmbh.co"></div>
      <div><label>메일 발신자</label><input id=sender placeholder="ap@bauer-gmbh.co"></div>
    </div>
    <label>메일 In-Reply-To (기존 스레드에 이어지면 값 입력)</label>
    <input id=in_reply_to placeholder="비우면 새 스레드로 간주">
    <button id=go>판정하기</button>
  </div>

  <div class=card>
    <h2>② 판정 결과</h2>
    <div id=out><div style="color:#999;font-size:13px">왼쪽에서 시나리오를 고르고 판정하기를 누르세요.</div></div>
  </div>
</div>

<div class=card style="margin-top:20px">
  <h2>③ 게이트가 읽은 계약서 (목업) — <code>data/demo/mock_contract.txt</code></h2>
  <div id=doc>불러오는 중…</div>
</div>
</div>

<script>
const S = __SCENARIOS__;
const F = ['account','bic','amount','currency','remittance_type','source','channel_detail','sender','in_reply_to'];
const sc = document.getElementById('sc');
Object.entries(S).forEach(([k,v],i)=>{
  const b=document.createElement('button'); b.textContent=v.label; b.dataset.k=k;
  b.onclick=()=>{ [...sc.children].forEach(c=>c.classList.remove('on')); b.classList.add('on');
    F.forEach(f=>document.getElementById(f).value = v.form[f] ?? '');
    document.getElementById('desc').textContent = v.desc; };
  sc.appendChild(b); if(i===0) setTimeout(()=>b.click(),0);
});
document.getElementById('go').onclick = async () => {
  const body={}; F.forEach(f=>body[f]=document.getElementById(f).value);
  const out=document.getElementById('out');
  out.innerHTML='<div style="color:#999;font-size:13px">판정 중…</div>';
  try{
    const r=await fetch('/judge',{method:'POST',headers:{'Content-Type':'application/json'},
                                 body:JSON.stringify(body)});
    const d=await r.json();
    if(d.error){ out.innerHTML='<pre>'+d.error+'\\n\\n'+(d.trace||'')+'</pre>'; return; }
    const KO={BLOCK_PENDING:'송금 보류 — 사람 승인 필요',HOLD:'보류 — 사람 승인 필요',
              UNKNOWN:'판정 불가 — 사람 승인 필요',PASS:'통과',NOTICE:'통과 (참고 사항 있음)'};
    out.innerHTML =
      '<div class="v '+d.verdict+'">'+(KO[d.verdict]||d.verdict)+
        '<small>'+d.verdict+' · 규칙 '+d.rule+'</small></div>'+
      (d.reasons.length? '<ul>'+d.reasons.map(x=>'<li>'+x.replace(/</g,'&lt;')+'</li>').join('')+'</ul>'
                       : '<div style="font-size:13px;color:#555">이 요청에서 발화한 위험 신호가 없습니다.</div>')+
      '<div class=meta>계약서 사실 출처: '+d.facts_origin+'</div>'+
      '<details><summary>발화 신호 · 추출된 계약서 사실 보기</summary><pre>'+
        JSON.stringify({신호:d.signals,계약서_사실:d.facts},null,1)+'</pre></details>';
  }catch(e){ out.innerHTML='<pre>요청 실패: '+e+'</pre>'; }
};
fetch('/contract').then(r=>r.text()).then(t=>document.getElementById('doc').textContent=t);
</script>
</html>"""


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
