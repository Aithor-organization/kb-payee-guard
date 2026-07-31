#!/usr/bin/env python3
"""v4 clause detector.

v3 audit showed the body path had ~50% precision: assignment clauses
("assign, license, transfer or CHANGE any of its rights ... under this
Agreement"), order-cancellation clauses ("cancel, reschedule, change or modify
any order"), and incorporation-by-reference prose ("the Quality Agreement, AS
AMENDED from time to time") all leaked in.

v4 requires the amendment term to be grammatically bound to the agreement:
  * a self-reference within 100 chars (agreement as subject or as object), AND
  * a writing requirement within 250 chars after it, AND
  * a modal/negation in the window, AND
  * NOT preceded by a transfer/cancel verb  -> kills assignment clauses, AND
  * NOT in "as (may be) amended" form        -> kills incorporation prose.
"""
import json, os, re, sys

OUT = "/Users/aithor/Documents/workspace/kb-payee-guard/data/contracts"

SENT = re.compile(r'[^.;]{20,1200}[.;]')
DOC = r'(?:this|the)\s+(?:[A-Z][A-Za-z]*\s+){0,3}(?:[Aa]greement|[Cc]ontract)'
AMEND_TERM = re.compile(r'(?i)\b(?:amend(?:ed|ment|ments|s)?|modif(?:y|ied|ication|ications)|'
                        r'var(?:y|ied|iation|iations)|alter(?:ed|ation|ations)?|'
                        r'supplement(?:ed|s)?|chang(?:e|ed|es))\b')
WRIT_TERM = re.compile(r'(?i)\b(?:in\s+writing|in\s+a\s+writing|by\s+a\s+writing|'
                       r'written\s+(?:instrument|agreement|amendment|document|consent|form|addendum)|'
                       r'signed\s+by|executed\s+by|in\s+written\s+form)\b')
SELF_REF = re.compile(r'(?i)\b(?:' + DOC + r'|hereof|hereto|herein|hereunder|'
                      r'the\s+present\s+(?:agreement|contract))\b')
CONSTRAINT = re.compile(r'(?i)\b(?:must|shall|may|will|can|not|only|unless|except|no|solely|'
                        r'save|valid|binding|effective|enforceable|invalid)\b')
# verbs that make the sentence about moving/killing rights, not amending the contract
XFER_VERB = re.compile(r'(?i)\b(?:assign|assigned|assignment|transfer|transferred|delegate|'
                       r'delegated|sublicense|sublicensed|cancel|cancelled|canceled|reschedule|'
                       r'rescheduled|terminate|terminated|revoke|revoked|withhold|withheld|'
                       r'disclose|disclosed|repair|repaired|misuse|reverse\s+engineer)\b')
# "as amended", "as may be amended", "as the same may be amended" = incorporation prose
AS_AMENDED = re.compile(r'(?i)\bas\s+(?:it\s+|the\s+same\s+|such\s+\w+\s+)?'
                        r'(?:may|might|shall|can|is|are|was|were)?\s*(?:be\s+)?$')

AMEND_HEAD = re.compile(
    r'(?mi)^[ \t]*(?:(?:ARTICLE|SECTION|CLAUSE)\s+)?'
    r'(?:\d+(?:\.\d+)*|[IVXLC]{1,6}|[A-Z]|\(\w{1,3}\))?[\.\)]?[ \t]*'
    r'(?:AMENDMENTS?|MODIFICATIONS?|VARIATIONS?|ALTERATIONS?|'
    r'AMENDMENTS?\s+AND\s+WAIVERS?|WAIVERS?\s+AND\s+AMENDMENTS?|'
    r'AMENDMENTS?\s*[;,]\s*WAIVERS?|AMENDMENTS?\s+IN\s+WRITING|'
    r'ENTIRE\s+AGREEMENT\s*[;,]\s*(?:AMENDMENTS?|MODIFICATIONS?)|'
    r'[A-Z][A-Za-z ]{0,30}\s*[;,]\s*(?:AMENDMENTS?|MODIFICATIONS?))'
    r'[ \t]*[:.\-–]?[ \t]*$')
AMEND_HEAD2 = re.compile(
    r'(?i)(?:ARTICLE|SECTION|CLAUSE)?\s*\d+(?:\.\d+)*[\.\)]\s*'
    r'(?:AMENDMENTS?|MODIFICATIONS?|AMENDMENTS?\s+AND\s+WAIVERS?|'
    r'AMENDMENTS?\s*[;,]\s*WAIVERS?|ENTIRE\s+AGREEMENT\s*[;,]\s*AMENDMENTS?)\b[ \t]*[:.\-–\n]')

NOTICE_HEAD = re.compile(
    r'(?mi)^[ \t]*(?:(?:ARTICLE|SECTION|CLAUSE)\s+)?'
    r'(?:\d+(?:\.\d+)*|[IVXLC]{1,6}|[A-Z]|\(\w{1,3}\))?[\.\)]?[ \t]*'
    r'(?:NOTICES?|NOTIFICATIONS?|NOTICES?\s+AND\s+[A-Z][A-Za-z ]{2,20}|'
    r'[A-Z][A-Za-z ]{0,30}\s*[;,]\s*NOTICES?)[ \t]*[:.\-–]?[ \t]*$')
NOTICE_HEAD2 = re.compile(
    r'(?i)(?:ARTICLE|SECTION|CLAUSE)?\s*\d+(?:\.\d+)*[\.\)]\s*'
    r'(?:NOTICES?|NOTICES\s+AND\s+DEMANDS|NOTICES\s*[;,]\s*\w+)\b[ \t]*[:.\-–\n]')
NOTICE_TERM = re.compile(r'(?i)\bnotices?\b')
# A notices clause states the MECHANICS of giving notice. Three ingredients:
#  (a) a general quantifier ("all/any/each/every notice") or a self-reference --
#      this is what separates §Notices from event-specific prose like
#      "Seller shall give written notice of any defect within 10 days";
#  (b) a writing requirement, a delivery CHANNEL, or a deemed-receipt rule,
#      within 220 chars after the notice term (drafters put long noun lists
#      -- "notices, consents, requests, demands and other communications" --
#      between the noun and its verb, so contiguity cannot be required).
NOTICE_QUANT = re.compile(r'(?i)\b(?:all|any|each|every|no)\s*$')
NOTICE_SCOPE = re.compile(r'(?i)\b(?:under\s+this|hereunder|required\s+or\s+permitted|'
                          r'pursuant\s+to\s+this|provided\s+for\s+(?:in|under)\s+this)\b')
NOTICE_OP = re.compile(r'(?i)(?:(?:shall|must|will|is\s+to|are\s+to|to)\s+be\s+'
                       r'(?:in\s+writing|given|sent|made|served|delivered|addressed|mailed|deemed)|'
                       r'\bin\s+writing\b|\bdeemed\s+(?:to\s+have\s+been\s+)?'
                       r'(?:duly\s+)?(?:given|received|delivered|served|made)\b|'
                       r'\bregistered\s+mail\b|\bcertified\s+mail\b|\brecorded\s+delivery\b|'
                       r'\bovernight\s+courier\b|\breceipted\s+courier\b|\bpostage\s+pre-?paid\b|'
                       r'\breturn\s+receipt\b|\bfacsimile\b|\btelecopier\b|'
                       r'\baddressed\s+to\b|\bdelivered\s+(?:personally|by\s+hand)\b)')
NOTICE_REF = re.compile(r'(?i)\b(?:' + DOC + r'|hereunder|hereto|herein|hereof|'
                        r'required\s+or\s+permitted|under\s+this|pursuant\s+to\s+this)\b')

PAY = re.compile(
    r'(?i)\b(?:letter\s+of\s+credit|documentary\s+credit|irrevocable\s+l/?c|\bL/C\b'
    r'|telegraphic\s+transfer|\bT/T\b|wire\s+transfer|electronic\s+funds\s+transfer|\bEFT\b|\bACH\b'
    r'|net\s+(?:thirty|sixty|ninety|\d{1,3})\s*(?:\(\d+\)\s*)?days?'
    r'|payment\s+terms?|terms\s+of\s+payment'
    r'|due\s+(?:and\s+payable\s+)?within\s+[\w\-]+\s*(?:\(\d+\))?\s*days'
    r'|(?:payable|paid|pay)\s+within\s+[\w\-]+\s*(?:\(\d+\)\s*)?days'
    r'|within\s+[\w\-]+\s*\(?\d*\)?\s*days\s+(?:of|after|from|following)\s+'
    r'(?:the\s+)?(?:date\s+of\s+)?(?:receipt\s+of\s+)?(?:the\s+)?invoice'
    r'|open\s+account|cash\s+in\s+advance|documents\s+against\s+(?:payment|acceptance)'
    r'|\bD/P\b|\bD/A\b|payment\s+shall\s+be\s+made)')

EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
ATTN = re.compile(r'(?i)\b(?:attention|attn)\s*[:\.]')
FAXPH = re.compile(r'(?i)\b(?:facsimile|telecopy|telecopier|fax|telephone|phone|tel)\s*'
                   r'(?:no\.?|number)?\s*[:\.]\s*(?:\+?[\d\(\)\-\s\.]{7,}|\.{3,}|_{3,})')
ADDR = re.compile(
    r'(?i)\b\d{1,6}\s+[A-Z][A-Za-z\.\'\-]+(?:\s+[A-Z][A-Za-z\.\'\-]+){0,4}\s+'
    r'(?:Street|St\.|Avenue|Ave\.|Road|Rd\.|Boulevard|Blvd\.|Drive|Dr\.|Lane|Ln\.|'
    r'Way|Parkway|Pkwy\.|Plaza|Court|Ct\.|Circle|Suite|Highway|Hwy\.)')
FILLIN = re.compile(r'(?i)(?:address|e-?mail|phone|fax|represented\s+by|notification\s+details)'
                    r'[^\n]{0,80}(?:\.\s*){4,}')


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def amend_sentence(text):
    for m in SENT.finditer(text):
        s = m.group(0)
        for a in AMEND_TERM.finditer(s):
            before = s[max(0, a.start() - 45):a.start()]
            if XFER_VERB.search(before) or AS_AMENDED.search(before):
                continue
            # "such CHANGED address" / "CHANGE of address" belongs to §Notices
            if re.match(r'(?i)\w*\s+(?:of\s+)?address', s[a.end():a.end() + 18]):
                continue
            # agreement must be bound to this amendment term (subject or object)
            near = s[max(0, a.start() - 200):a.end() + 120]
            if not SELF_REF.search(near):
                continue
            w = WRIT_TERM.search(s, a.end())
            if not w or w.start() - a.end() > 250:
                w = WRIT_TERM.search(s[max(0, a.start() - 150):a.start()])
                if not w:
                    continue
                win = s[max(0, a.start() - 150):a.end() + 40]
            else:
                win = s[max(0, a.start() - 60):w.end()]
            if not CONSTRAINT.search(win):
                continue
            return clean(s)
    return None


def notice_sentence(text):
    for m in SENT.finditer(text):
        s = m.group(0)
        for n in NOTICE_TERM.finditer(s):
            before = s[max(0, n.start() - 12):n.start()]
            # look past the sentence end: drafters break mid-clause with "etc."
            abs_end = m.start() + n.end()
            after = text[abs_end:abs_end + 300]
            general = NOTICE_QUANT.search(before) or NOTICE_SCOPE.search(after[:90])
            if not general:
                continue
            if NOTICE_OP.search(after):
                return clean(s)
    return None


def detect(text):
    r, ev = {}, {}
    h = NOTICE_HEAD.search(text) or NOTICE_HEAD2.search(text)
    s = notice_sentence(text)
    r['notices'] = 'Y' if (h or s) else 'N'
    r['notices_how'] = 'heading' if h else ('body' if s else '')
    ev['notices'] = (clean(text[h.start():h.start() + 300]) if h else s) if (h or s) else ''

    h = AMEND_HEAD.search(text) or AMEND_HEAD2.search(text)
    s = amend_sentence(text)
    r['amendment'] = 'Y' if (h or s) else 'N'
    r['amendment_how'] = 'heading' if h else ('body' if s else '')
    ev['amendment'] = (clean(text[h.start():h.start() + 300]) if h else s) if (h or s) else ''

    p = PAY.search(text)
    r['payment'] = 'Y' if p else 'N'
    ev['payment'] = clean(text[max(0, p.start() - 110):p.end() + 190]) if p else ''

    sig = [(k, m) for k, m in (('email', EMAIL.search(text)), ('attn', ATTN.search(text)),
                               ('fax/phone', FAXPH.search(text)), ('address', ADDR.search(text)),
                               ('fill-in', FILLIN.search(text))) if m]
    r['contact'] = 'Y' if sig else 'N'
    r['contact_signals'] = ','.join(k for k, _ in sig)
    ev['contact'] = clean(text[max(0, sig[0][1].start() - 90):sig[0][1].end() + 170]) if sig else ''
    return r, ev


def main():
    rows, evid = [], {}
    for f in sorted(os.listdir(OUT)):
        if not f.endswith('.txt') or f.startswith('_'):
            continue
        t = open(os.path.join(OUT, f), errors='replace').read()
        r, e = detect(t)
        r['file'], r['chars'] = f, len(t)
        rows.append(r)
        evid[f] = e
    json.dump(rows, open(os.path.join(OUT, '_detect.json'), 'w'), indent=1)
    json.dump(evid, open(os.path.join(OUT, '_evidence.json'), 'w'), indent=1)

    def agg(rs, label):
        n = len(rs)
        if not n:
            return
        for c in ('notices', 'amendment', 'payment', 'contact'):
            y = sum(1 for x in rs if x[c] == 'Y')
            print(f"{label:6s} {c:10s} {y:3d}/{n:3d} = {100*y/n:5.1f}%")
        print()
    agg([r for r in rows if r['file'].startswith(('sec-', 'cuad-'))], 'REAL')
    agg([r for r in rows if r['file'].startswith('itc-')], 'MODEL')
    print('total', len(rows))


if __name__ == '__main__':
    main()
