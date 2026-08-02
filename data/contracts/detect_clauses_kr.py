#!/usr/bin/env python3
"""Korean clause detector — mirrors the project's v4 English detector semantics.

Same discipline as detect_clauses.py: a clause counts only when the document
states the MECHANICS (§Notices) or a binding constraint on the contract itself
(§Amendment), not when it merely mentions a one-off notice/change duty.
"""
import json, os, re, sys

C = "/Users/aithor/Documents/workspace/kb-payee-guard/data/contracts"

# ---- article headings: 제12조(통지) / 제12조의2(계약의 변경) ----
def head(pat):
    return re.compile(r"제\d+조(?:의\d+)?\s*\(\s*[^)\n]{0,24}" + pat + r"[^)\n]{0,24}\s*\)")

# 🔴 Korean article titles are DESCRIPTIVE ("제24조(납품예정일자의 통지)"), unlike the
# English "§Notices". Matching any title containing 통지/통보 gave 21 false positives
# out of 34 in the hand audit (변동사항 통보의무 / 우대가격 통보의무 / 납품지체 통지 /
# 선적 통보 …) — all event-specific duties, not notice mechanics. So the title must be
# ABOUT notice itself, with only generic modifiers allowed.
ART = re.compile(r"제(\d+)조(?:의\d+)?\s*\(\s*([^)\n]{1,40}?)\s*\)")
NOTICE_TITLE = re.compile(
    r"^(?:(?:서\s*면|상\s*호|계약당사자\s*간의?|양?\s*당사자\s*간의?|"
    r"(?:회원|이용자|당사자|상대방)에\s*대한)\s*)?"
    r"(?:통\s*지|통\s*보|연\s*락)"
    r"(?:\s*(?:등|및\s*(?:연락|공지|통보)|공지|방법|의?\s*방법|장소|의?\s*효력|수령))*\s*$")


def notice_heading(t):
    for m in ART.finditer(t):
        if NOTICE_TITLE.match(m.group(2)):
            return m
    return None
AMEND_HEAD = head(r"(?:계약\s*내용의?\s*변경|계약의?\s*변경|변경계약|계약조건의?\s*변경|"
                  r"계약의?\s*수정|수정계약|계약서의?\s*변경|계약의?\s*변동|"
                  r"약관의?\s*(?:변경|개정)|조건의?\s*(?:변경|개정))")
# bare 지급 over-matched ("계약보증금 면제 및 지급각서 제출") — require a payment object
PAY_HEAD = head(r"(?:대가의?\s*지급|대가지급|대금의?\s*지급|대금지급|선금(?:지급)?|기성대가|"
                r"기성부분금|이용대금|리스료|금전지급|지급방법|지급조건|대가\s*등의\s*지급|"
                r"하도급대금|대금결제|결제조건|결제방법|지불방법|대가의?\s*지불|보수\s*지불|대가지불|정보제공료|정보이용료|정산방법|이용료|수수료)")

SENT = re.compile(r"[^.\n]{15,700}[.\n]")

# --- §Notices body path: the notice term must be GENERAL, not tied to one event ---
N_TERM = re.compile(r"통\s*지|통\s*보")
# quantifier immediately before the term (mirrors English NOTICE_QUANT)
N_QUANT = re.compile(r"(모든|일체의|각종|일체\s*의|제반)\s*(?:[가-힣]{0,6}\s*)?$")
# or an explicit scope tie to THIS contract right before the term
N_SCOPE = re.compile(r"(이|본)\s*계약(?:에\s*따른|상의|과\s*관련된|에\s*의한|에\s*기한)?\s*"
                     r"(?:[가-힣]{0,8}\s*)?$|계약당사자\s*간의?\s*$|"
                     r"(?:구두에\s*의한)\s*$")
# and the sentence must state MECHANICS, not merely "notify X"
N_CHAN = re.compile(r"(서\s*면으로\s*(?:하|한다|하여야|함)|서면에\s*의|서면통지|문서로\s*(?:보완|한다|하여야)|"
                    r"전자우편(?:주소)?로|이메일로|내용증명|등기우편|우편으로|모사전송|"
                    r"계약서에\s*기재된\s*주소|지정한?\s*주소로|주소로\s*(?:우편|발송|송부)|"
                    r"도달(?:한|된)\s*(?:때|날)|수령한\s*것으로\s*본다|효력이\s*(?:있다|발생))")
N_OBL = re.compile(r"(하여야\s*한다|해야\s*한다|한\s*다|합니다|하여야|본다|간주|있다)")

# --- §Amendment: contract self-reference + change + writing/agreement + modality ---
A_TERM = re.compile(r"변\s*경|수\s*정|개\s*정")
# NOTE: 계약금액/계약기간 are deliberately NOT self-references — "계약금액의 조정"
# (price adjustment) and "계약기간 연장" are their own institutions in Korean public
# contracts and are not an amendment-in-writing clause. Including them produced
# false positives (kr-024 audit).
A_SELF = re.compile(r"(이\s*계약|본\s*계약|이\s*조건|이\s*약관|계약의?\s*내용|계약\s*내용|"
                    r"계약조건|계약서|수정계약|변경계약)")
# the change must target THIS contract, not a person or a different (sub)contract
A_OTHER = re.compile(r"(하도급|하수급인|재하도급|공동수급체\s*구성원|현장대리인|참여기술인|"
                     r"기술인의?\s*배치|담당자|대표자|주소|상호)")
A_WRIT = re.compile(r"(서\s*면|문\s*서|계약서|합\s*의|협\s*의|변경계약|계약을?\s*변경|"
                    r"서명|기명날인|전자문서)")
A_MOD = re.compile(r"(하여야\s*한다|해야\s*한다|할\s*수\s*있다|하지\s*못한다|없다|"
                   r"한\s*다|아니한다|경우에\s*한(?:하여|한다))")

PAY = re.compile(r"(신용장|Letter\s*of\s*Credit|\bL/C\b|전신환|전신송금|\bT/T\b|"
                 r"지급인도조건|인수인도조건|\bD/P\b|\bD/A\b|"
                 r"대가의?\s*지급|대금(?:을|의)?\s*지급|지급기한|지급조건|선\s*금|기성대가|"
                 r"청구를?\s*받은\s*날(?:부터|로부터)\s*\d+일|"
                 r"\d+일\s*이내에\s*(?:이를\s*)?지급|대금을?\s*지급하여야|대가의?\s*지불|대금(?:을|의)?\s*지불|정보제공료|정보이용료|보수를?\s*지[급불])")

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
CONTACT = re.compile(r"(주\s*소\s*[:：]|전화번호|연락처|팩스|담당자|전자우편\s*주소|이메일\s*주소|"
                     r"소재지|대표자\s*[:：]|사업자등록번호)")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def bound_sentence(text, term, need, mod, self_ref=None, gen=None, win=160, excl=None):
    for m in SENT.finditer(text):
        s = m.group(0)
        for t in term.finditer(s):
            lo, hi = max(0, t.start() - win), min(len(s), t.end() + win)
            w = s[lo:hi]
            if excl is not None and excl.search(s[max(0, t.start() - 30):t.start()]):
                continue
            if gen is not None and not gen.search(w):
                continue
            if self_ref is not None and not self_ref.search(w):
                continue
            if not need.search(w) or not mod.search(s[t.end():] or s):
                continue
            return clean(s)
    return None


# body path: a bare mention inside an incorporation-by-reference list
# ("대가의 지급, 기성검사 … 등은 일반조건에 따른다") is a pointer, not payment terms —
# same exclusion the English v4 makes for "as amended" prose.
PAY_OBL = re.compile(r"(지급하여야|지급한다|지급하고|지급할\s*수|지급하지|지급받|지급기한|"
                     r"이내에\s*(?:이를\s*)?지급|지급을?\s*(?:하|청구|신청)|개설|발급을?\s*신청|"
                     r"지급합니다|납부하여야|지불하여야|지불한다|지불하고|지불할\s*수|지불합니다)")
PAY_REF = re.compile(r"(정한\s*바에\s*따른다|에\s*따른다\.|규정한\s*바에|준용한다|"
                     r"일반조건|특수조건)\s*$")


def pay_sentence(text):
    for m in SENT.finditer(text):
        s = m.group(0)
        p = PAY.search(s)
        if not p:
            continue
        if PAY_REF.search(s[p.end():]):
            continue
        if PAY_OBL.search(s[p.end():p.end() + 80]):
            return clean(s)
    return None


def notice_sentence(text):
    """General notice-mechanics sentence: quantifier/scope immediately before the
    term, plus an actual channel or deemed-receipt rule after it."""
    for m in SENT.finditer(text):
        s = m.group(0)
        for n in N_TERM.finditer(s):
            before = s[max(0, n.start() - 24):n.start()]
            if not (N_QUANT.search(before) or N_SCOPE.search(before)):
                continue
            after = s[n.end():n.end() + 220]
            if N_CHAN.search(after) and N_OBL.search(after):
                return clean(s)
    return None


def detect(t):
    r, ev = {}, {}
    h = notice_heading(t)
    s = notice_sentence(t)
    r["notices"] = "Y" if (h or s) else "N"
    r["notices_how"] = "heading" if h else ("body" if s else "")
    ev["notices"] = clean(t[h.start():h.start() + 260]) if h else (s or "")

    h = AMEND_HEAD.search(t)
    s = bound_sentence(t, A_TERM, A_WRIT, A_MOD, self_ref=A_SELF, excl=A_OTHER)
    r["amendment"] = "Y" if (h or s) else "N"
    r["amendment_how"] = "heading" if h else ("body" if s else "")
    ev["amendment"] = clean(t[h.start():h.start() + 260]) if h else (s or "")

    h = PAY_HEAD.search(t)
    p = pay_sentence(t)
    r["payment"] = "Y" if (h or p) else "N"
    r["payment_how"] = "heading" if h else ("body" if p else "")
    ev["payment"] = clean(t[h.start():h.start() + 260]) if h else (p or "")

    e = EMAIL.search(t)
    c = CONTACT.search(t)
    r["email"] = "Y" if e else "N"
    r["contact"] = "Y" if (e or c) else "N"
    ev["contact"] = clean(t[max(0, (e or c).start() - 80):(e or c).end() + 150]) if (e or c) else ""
    return r, ev


def main():
    pref = sys.argv[1] if len(sys.argv) > 1 else "kr-"
    rows, evs = [], {}
    for f in sorted(os.listdir(C)):
        if not f.startswith(pref) or not f.endswith(".txt"):
            continue
        t = open(os.path.join(C, f), errors="replace").read()
        r, e = detect(t)
        r["file"], r["chars"] = f, len(t)
        rows.append(r)
        evs[f] = e
    SP = os.path.dirname(os.path.abspath(__file__))
    json.dump(rows, open(f"{SP}/detect_kr.json", "w"), ensure_ascii=False, indent=1)
    json.dump(evs, open(f"{SP}/evid_kr.json", "w"), ensure_ascii=False, indent=1)
    n = len(rows)
    print("n =", n)
    for c in ("notices", "amendment", "payment", "contact", "email"):
        y = sum(1 for x in rows if x[c] == "Y")
        print(f"  {c:10s} {y:3d}/{n:3d} = {100*y/n:5.1f}%")


if __name__ == "__main__":
    main()
