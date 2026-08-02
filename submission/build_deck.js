/**
 * 기술설명서 생성 — 제8회 KB A.I Challenge 예선
 *
 * 슬라이드는 심사배점에 1:1로 대응시킨다 (공고 "예선 평가 기준", 2026-07-24):
 *   문제해결능력 50 = 문제정의·필요성 15 / 활용 가능성 15 / 창의성·효과 20
 *   기술적완성도 50 = 기술 적정성 20 / 개발계획 구체성 15 / 기술 실현가능성 15
 *
 * 🔴 수치는 전부 저장소의 실측 문서에서 가져온다. 이 파일에서 새로 만들지 않는다.
 *    출처: docs/03_R7_측정.md · docs/05_베이스라인A_실측.md · docs/06_E2E_탐지율_오탐률.md
 *
 * 실행: node submission/build_deck.js
 */
const pptxgen = require("pptxgenjs");

// ── 팔레트 ────────────────────────────────────────────────────────────────
// 무역송금 사기 방지 = 서류·경보·차단. 딥 잉크 네이비가 지배하고,
// 앰버는 "보류(HOLD)", 벽돌색은 "차단(BLOCK)" 신호로만 쓴다 — 장식이 아니라 의미다.
const INK = "0F2740";      // 지배색
const INK_2 = "1B3C5E";    // 카드 배경
const PAPER = "EEF2F6";    // 밝은 본문 배경
const AMBER = "E8A33D";    // 보류·강조
const BRICK = "C1443C";    // 차단·위험
const MINT = "3FA894";     // 통과·성공
const MUTED = "8FA3B8";

const H = "Georgia";       // 제목
const B = "Calibri";       // 본문

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";           // 10 × 5.625 in
pres.title = "KB Payee Guard — 기술설명서";
pres.author = "KB Payee Guard";

const W = 10, HT = 5.625, M = 0.55;

/** 어두운 본문 슬라이드 + 좌측 앰버 바 (전 슬라이드 공통 모티프) */
function slide(titleText, kicker) {
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.12, h: HT, fill: { color: AMBER } });
  if (kicker) {
    s.addText(kicker, {
      x: M, y: 0.3, w: W - M * 2, h: 0.25, fontSize: 11, fontFace: B,
      color: AMBER, bold: true, charSpacing: 2, margin: 0,
    });
  }
  s.addText(titleText, {
    x: M, y: kicker ? 0.58 : 0.42, w: W - M * 2, h: 0.72,
    fontSize: 30, fontFace: H, color: "FFFFFF", bold: true, margin: 0,
  });
  return s;
}

/** 카드 (배경 사각형 + 안쪽 텍스트) */
function card(s, { x, y, w, h, fill = INK_2, radius = 0.08 }) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: fill }, rectRadius: radius,
    line: { color: fill, width: 0 },
  });
}

/** 큰 숫자 + 라벨 */
function stat(s, { x, y, w, value, label, color = AMBER, sub }) {
  s.addText(value, {
    x, y, w, h: 0.72, fontSize: 40, fontFace: H, bold: true, color,
    align: "center", margin: 0,
  });
  s.addText(label, {
    x, y: y + 0.74, w, h: 0.3, fontSize: 12, fontFace: B, color: "FFFFFF",
    align: "center", margin: 0,
  });
  if (sub) {
    s.addText(sub, {
      x, y: y + 1.03, w, h: 0.26, fontSize: 10, fontFace: B, color: MUTED,
      align: "center", margin: 0,
    });
  }
}

function footnote(s, text) {
  s.addText(text, {
    x: M, y: HT - 0.42, w: W - M * 2, h: 0.28, fontSize: 9, fontFace: B,
    color: MUTED, italic: true, margin: 0,
  });
}

// ══ 1. 표지 ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.12, h: HT, fill: { color: AMBER } });
  s.addText("제8회 KB A.I Challenge · 예선 기술설명서 · 금융 자유주제", {
    x: M, y: 0.7, w: W - M * 2, h: 0.3, fontSize: 12, fontFace: B,
    color: AMBER, bold: true, charSpacing: 1.5, margin: 0,
  });
  s.addText("KB Payee Guard", {
    x: M, y: 1.35, w: W - M * 2, h: 1.0, fontSize: 52, fontFace: H,
    bold: true, color: "FFFFFF", margin: 0,
  });
  s.addText("계약서 기반 해외송금 무결성 게이트", {
    x: M, y: 2.35, w: W - M * 2, h: 0.5, fontSize: 22, fontFace: B,
    color: PAPER, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 3.05, w: 2.2, h: 0.03, fill: { color: AMBER } });
  s.addText([
    { text: "법으로 이미 제출되는 계약서", options: { bold: true, color: AMBER } },
    { text: "를 읽어, 계좌 변경 지시가 계약이 정한 절차를 따랐는지 대조합니다." },
  ], {
    x: M, y: 3.35, w: 7.6, h: 0.6, fontSize: 15, fontFace: B, color: "FFFFFF", margin: 0,
  });
  s.addText([
    { text: "경쟁 제품은 계좌라는 ", options: {} },
    { text: "값", options: { bold: true, color: BRICK } },
    { text: "을 검증합니다. 값은 사기범이 통제할 수 있습니다.\n", options: {} },
    { text: "우리는 그 값이 온 ", options: {} },
    { text: "경로", options: { bold: true, color: MINT } },
    { text: "를 검증합니다. 경로 규칙은 계약 체결 시점에 잠겨 있습니다.", options: {} },
  ], {
    x: M, y: 4.15, w: 8.4, h: 0.9, fontSize: 13, fontFace: B, color: PAPER,
    lineSpacing: 20, margin: 0,
  });
}

// ══ 2. 문제 (문제정의 15) ════════════════════════════════════════════════
{
  const s = slide("메일 한 통에 대금 전액이 사라집니다", "문제 정의");
  card(s, { x: M, y: 1.5, w: 5.5, h: 2.5 });
  s.addText([
    { text: '"회계감사로 거래 은행을 변경했습니다.\n새 계좌로 송금 부탁드립니다."\n\n', options: { italic: true, color: AMBER, breakLine: true } },
    { text: "3년 거래한 담당자 이름, 첨부된 인보이스, 늘 쓰던 서명.\n12만 유로를 송금합니다.\n\n", options: { breakLine: true } },
    { text: "3주 뒤 — ", options: {} },
    { text: '"대금이 아직 안 들어왔는데요."', options: { bold: true, color: BRICK } },
  ], {
    x: M + 0.3, y: 1.75, w: 4.9, h: 2.0, fontSize: 13, fontFace: B,
    color: "FFFFFF", lineSpacing: 19, margin: 0,
  });
  s.addText("도메인이 @bauer-gmbh.de 가 아니라 @bauer-gmbh.co 였습니다 — 글자 하나.", {
    x: M + 0.3, y: 3.55, w: 4.9, h: 0.35, fontSize: 11, fontFace: B, color: MUTED, margin: 0,
  });

  stat(s, { x: 6.3, y: 1.5, w: 1.6, value: "1,600건", label: "국내 접수", color: AMBER, sub: "2021~25 상반기" });
  stat(s, { x: 8.0, y: 1.5, w: 1.6, value: "전액", label: "건당 손실", color: BRICK, sub: "부분 손실 없음" });
  card(s, { x: 6.3, y: 3.0, w: 3.3, h: 1.0 });
  s.addText([
    { text: "회수 가능성 ", options: {} },
    { text: "사실상 0", options: { bold: true, color: BRICK } },
    { text: "\n해외 계좌에서 즉시 인출됩니다.", options: { breakLine: true } },
  ], {
    x: 6.55, y: 3.2, w: 2.9, h: 0.7, fontSize: 12, fontFace: B, color: "FFFFFF",
    lineSpacing: 17, margin: 0,
  });
  footnote(s, "출처: 금융감독원 / KBS 보도 · 회수 불가는 KOTRA 매뉴얼");
}

// ══ 3. 왜 안 잡히나 (문제정의 15) ═══════════════════════════════════════
{
  const s = slide("기존 방어선이 전부 비껴가는 케이스가 있습니다", "문제 정의");
  const rows = [
    ["메일 보안 (Proofpoint · Trend Micro)", "도메인·문체를 봅니다", "계정이 탈취되면 도메인이 진짜입니다", BRICK],
    ["벤더 마스터 (Trustpair · Eftsure)", "과거 계좌 이력을 봅니다", "정당한 변경과 사기를 못 가릅니다", BRICK],
    ["이름 대조 (EU VoP · iPiD · 국내 은행)", "이름↔계좌를 봅니다", "법인명으로 계좌를 열면 통과합니다", BRICK],
  ];
  let y = 1.45;
  rows.forEach(([who, what, why, c]) => {
    card(s, { x: M, y, w: W - M * 2, h: 0.82 });
    s.addText(who, { x: M + 0.25, y: y + 0.12, w: 3.2, h: 0.28, fontSize: 12, fontFace: B, bold: true, color: "FFFFFF", margin: 0 });
    s.addText(what, { x: M + 0.25, y: y + 0.42, w: 3.2, h: 0.28, fontSize: 10, fontFace: B, color: MUTED, margin: 0 });
    s.addText(why, { x: 4.2, y: y + 0.26, w: 5.1, h: 0.34, fontSize: 12, fontFace: B, color: c, bold: true, margin: 0 });
    y += 0.95;
  });
  card(s, { x: M, y: 4.32, w: W - M * 2, h: 0.72, fill: "24506B" });
  s.addText([
    { text: "그럼 무엇이 남는가? ", options: { bold: true, color: AMBER } },
    { text: "계좌번호가 바뀌었다는 사실, 그리고 ", options: {} },
    { text: "그 지시가 계약서가 정한 경로로 오지 않았다는 사실", options: { bold: true, color: MINT } },
    { text: "입니다.", options: {} },
  ], {
    x: M + 0.25, y: 4.5, w: 8.6, h: 0.4, fontSize: 13, fontFace: B, color: "FFFFFF", margin: 0,
  });
  footnote(s, "벤더 자신의 인정: \"사기범이 정확한 법인명으로 계좌를 개설하면 이름 대조는 통과한다\" — Eftsure");
}

// ══ 4. 빈 구간 (활용 가능성 15) ═════════════════════════════════════════
{
  const s = slide("규제는 지시했고, 서류는 이미 옵니다", "활용 가능성");
  card(s, { x: M, y: 1.4, w: 4.5, h: 1.65, fill: INK_2 });
  s.addText("금융감독원 → 전 은행", { x: M + 0.25, y: 1.55, w: 4.0, h: 0.3, fontSize: 11, fontFace: B, bold: true, color: AMBER, margin: 0 });
  s.addText('"수취인 국가와 수취 은행 소재 국가가 서로 다르거나 계좌번호가 평소와 다른 경우 다시 확인하는 절차를 거치도록"', {
    x: M + 0.25, y: 1.87, w: 4.0, h: 1.0, fontSize: 11, fontFace: B, color: "FFFFFF", italic: true, lineSpacing: 16, margin: 0,
  });

  card(s, { x: 5.35, y: 1.4, w: 4.1, h: 1.65, fill: INK_2 });
  s.addText("외국환거래법", { x: 5.6, y: 1.55, w: 3.6, h: 0.3, fontSize: 11, fontFace: B, bold: true, color: AMBER, margin: 0 });
  s.addText("연 10만 달러 초과 송금은 계약서 등 지급 사유 입증 서류 제출 의무. 은행은 이미 계약서를 받고 있습니다.", {
    x: 5.6, y: 1.87, w: 3.6, h: 1.0, fontSize: 11, fontFace: B, color: "FFFFFF", lineSpacing: 16, margin: 0,
  });

  card(s, { x: M, y: 3.25, w: W - M * 2, h: 1.15, fill: "24506B" });
  s.addText([
    { text: "은행은 그 계약서로 ", options: {} },
    { text: "\"정당한 거래 목적인가\"", options: { bold: true } },
    { text: "(자금세탁 방지)를 확인합니다.\n", options: { breakLine: true } },
    { text: "그런데 계약서가 정한 상대방·결제조건·계좌 변경 절차와 실제 송금이 일치하는지는 ", options: {} },
    { text: "확인하지 않습니다.", options: { bold: true, color: AMBER } },
  ], {
    x: M + 0.28, y: 3.45, w: 8.5, h: 0.8, fontSize: 13, fontFace: B, color: "FFFFFF", lineSpacing: 20, margin: 0,
  });
  s.addText("서류는 이미 옵니다. 아무도 읽지 않을 뿐입니다.", {
    x: M, y: 4.62, w: 8.9, h: 0.35, fontSize: 15, fontFace: H, bold: true, color: MINT, margin: 0,
  });
}

// ══ 5. 핵심 아이디어 (창의성 20) ════════════════════════════════════════
{
  const s = slide("계좌라는 값이 아니라, 그 값이 온 경로를 봅니다", "창의성");
  card(s, { x: M, y: 1.4, w: 4.3, h: 2.15, fill: INK_2 });
  s.addText("제출된 계약서 (2023-04-11)", { x: M + 0.25, y: 1.55, w: 3.8, h: 0.3, fontSize: 11, fontFace: B, bold: true, color: MUTED, margin: 0 });
  s.addText([
    { text: "상대방      BAUER GmbH\n", options: { breakLine: true } },
    { text: "소재지      Stuttgart, Germany\n", options: { breakLine: true } },
    { text: "결제조건    Irrevocable L/C\n", options: { breakLine: true } },
    { text: "§14 변경    ", options: {} },
    { text: '"서면 합의로만"', options: { bold: true, color: AMBER } },
  ], {
    x: M + 0.25, y: 1.92, w: 3.8, h: 1.5, fontSize: 12, fontFace: "Consolas",
    color: "FFFFFF", lineSpacing: 22, margin: 0,
  });

  card(s, { x: 5.2, y: 1.4, w: 4.25, h: 2.15, fill: INK_2 });
  s.addText("이번 송금 신청", { x: 5.45, y: 1.55, w: 3.8, h: 0.3, fontSize: 11, fontFace: B, bold: true, color: MUTED, margin: 0 });
  s.addText([
    { text: "수취계좌    LT12 … 47  (리투아니아)\n", options: { breakLine: true } },
    { text: "송금방식    T/T\n", options: { breakLine: true } },
    { text: "계좌 지시   ", options: {} },
    { text: "이메일", options: { bold: true, color: BRICK } },
  ], {
    x: 5.45, y: 1.92, w: 3.8, h: 1.5, fontSize: 12, fontFace: "Consolas",
    color: "FFFFFF", lineSpacing: 22, margin: 0,
  });

  const sigs = [
    ["S16", "계약 §14는 서면 합의를 요구하는데 이번 지시는 이메일", AMBER],
    ["S9", "계약 상대방은 독일인데 계좌 개설국이 리투아니아", AMBER],
    ["S10", "계약은 L/C인데 이번엔 T/T — 은행 보증이 사라집니다", AMBER],
  ];
  let y = 3.72;
  sigs.forEach(([id, txt, c]) => {
    s.addShape(pres.shapes.OVAL, { x: M, y, w: 0.42, h: 0.42, fill: { color: c } });
    s.addText(id, { x: M, y: y + 0.03, w: 0.42, h: 0.36, fontSize: 10, fontFace: B, bold: true, color: INK, align: "center", margin: 0 });
    s.addText(txt, { x: M + 0.55, y: y + 0.06, w: 8.3, h: 0.32, fontSize: 12, fontFace: B, color: "FFFFFF", margin: 0 });
    y += 0.5;
  });
  footnote(s, "§Notices·§Amendment는 계약 체결 시점에 확정됩니다 — 사기범이 사후에 바꿀 수 없습니다.");
}

// ══ 6. AI 필연성 (기술 적정성 20) ═══════════════════════════════════════
{
  const s = slide("AI가 없으면 이 제품은 성립하지 않습니다", "기술 적정성 · 실측");
  s.addText([
    { text: "S16의 계산은  [계약이 허용한 경로] ∩ [이번 지시가 온 경로]  입니다.\n", options: { breakLine: true } },
    { text: "오른쪽은 은행이 신청 폼으로 묻습니다. 왼쪽은 ", options: {} },
    { text: "계약서 자연어에만", options: { bold: true, color: AMBER } },
    { text: " 있습니다.", options: {} },
  ], {
    x: M, y: 1.42, w: 8.9, h: 0.7, fontSize: 13, fontFace: B, color: "FFFFFF", lineSpacing: 20, margin: 0,
  });

  card(s, { x: M, y: 2.2, w: 4.35, h: 1.9, fill: "3A2320" });
  s.addText("정규식 추출", { x: M + 0.25, y: 2.35, w: 3.8, h: 0.3, fontSize: 12, fontFace: B, bold: true, color: BRICK, margin: 0 });
  stat(s, { x: M + 0.1, y: 2.68, w: 2.0, value: "30.0%", label: "정확도", color: BRICK });
  stat(s, { x: M + 2.15, y: 2.68, w: 2.0, value: "20.8%", label: "재현율", color: BRICK });

  card(s, { x: 5.2, y: 2.2, w: 4.25, h: 1.9, fill: "12352E" });
  s.addText("LLM 추출", { x: 5.45, y: 2.35, w: 3.8, h: 0.3, fontSize: 12, fontFace: B, bold: true, color: MINT, margin: 0 });
  stat(s, { x: 5.3, y: 2.68, w: 2.0, value: "90.0%", label: "정확도", color: MINT });
  stat(s, { x: 7.35, y: 2.68, w: 2.0, value: "91.7%", label: "재현율", color: MINT });

  s.addText([
    { text: "정규식은 해석에서 지기 전에 ", options: {} },
    { text: "조항을 찾지 못합니다", options: { bold: true, color: AMBER } },
    { text: " — 오답 21건 중 19건이 미탐지.\n계약서마다 조항의 제목·번호 체계·배치가 다르고 본문에 섞여 있기 때문입니다.", options: { breakLine: true } },
  ], {
    x: M, y: 4.22, w: 8.9, h: 0.7, fontSize: 12, fontFace: B, color: PAPER, lineSpacing: 18, margin: 0,
  });
  footnote(s, "실물 계약서 30건 전수 · 합격선(재현율 ≥90%)은 측정 전에 고정 · docs/05_베이스라인A_실측.md");
}

// ══ 7. 게이트 성능 (창의성·효과 20) ═════════════════════════════════════
{
  const s = slide("무엇을 막고 무엇을 통과시키나", "효과 · 실측");
  stat(s, { x: M, y: 1.5, w: 2.6, value: "93.3%", label: "BEC 탐지율", color: MINT, sub: "LLM 추출 경유" });
  stat(s, { x: 3.3, y: 1.5, w: 2.6, value: "0.0%", label: "정상거래 오탐률", color: MINT, sub: "정상 시나리오 2종" });
  stat(s, { x: 6.1, y: 1.5, w: 2.6, value: "16.7%", label: "정규식 경유 탐지율", color: BRICK, sub: "게이트가 사실상 꺼짐" });

  card(s, { x: M, y: 3.05, w: W - M * 2, h: 1.05, fill: "3A2320" });
  s.addText([
    { text: "🔴 알려진 사각지대 — 위조 수정합의서는 통과합니다 (30건 전건 미탐)\n", options: { bold: true, color: BRICK, breakLine: true } },
    { text: "S16은 지시의 ", options: {} },
    { text: "경로", options: { bold: true } },
    { text: "를 보지 문서의 ", options: {} },
    { text: "진위", options: { bold: true } },
    { text: "를 보지 않습니다. 통과할 것을 알면서 평가셋에 넣었습니다.", options: {} },
  ], {
    x: M + 0.28, y: 3.22, w: 8.5, h: 0.75, fontSize: 12, fontFace: B, color: "FFFFFF", lineSpacing: 18, margin: 0,
  });
  s.addText("정상 시나리오를 넣은 것이 핵심입니다 — 오탐률 없는 탐지율은 의미가 없습니다. 전부 차단하면 100%입니다.", {
    x: M, y: 4.25, w: 8.9, h: 0.35, fontSize: 12, fontFace: B, color: PAPER, margin: 0,
  });
  footnote(s, "실물 계약서 30건 × 시나리오 5 = 150건 전수. 자체 설계 시나리오이며 실제 사기 탐지 성능이 아닙니다 — docs/06 §5");
}

// ══ 8. 안전 설계 (기술 적정성 20) ═══════════════════════════════════════
{
  const s = slide("LLM은 판정하지 않습니다 — 코드가 강제합니다", "기술 적정성");
  const items = [
    ["1", "판정 권한이 스키마에 없다", "추출 스키마에 verdict·score·approve 필드가 존재하지 않습니다. 등급은 결정론 규칙 테이블이 정합니다."],
    ["2", "지시와 데이터를 분리한다", "계약서 본문은 system이 아니라 user 메시지의 구분자 안에만 들어갑니다."],
    ["3", "근거를 원문과 대조한다", "LLM이 반환한 근거 구간이 원문에 없으면 그 값을 버립니다. 인젝션이 노리는 건 등급이 아니라 추출값입니다."],
  ];
  let y = 1.45;
  items.forEach(([n, head, body]) => {
    s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.06, w: 0.46, h: 0.46, fill: { color: AMBER } });
    s.addText(n, { x: M, y: y + 0.1, w: 0.46, h: 0.4, fontSize: 15, fontFace: H, bold: true, color: INK, align: "center", margin: 0 });
    s.addText(head, { x: M + 0.62, y: y + 0.02, w: 8.2, h: 0.32, fontSize: 14, fontFace: B, bold: true, color: "FFFFFF", margin: 0 });
    s.addText(body, { x: M + 0.62, y: y + 0.36, w: 8.2, h: 0.55, fontSize: 11.5, fontFace: B, color: PAPER, lineSpacing: 16, margin: 0 });
    y += 1.05;
  });
  card(s, { x: M, y: 4.5, w: W - M * 2, h: 0.72, fill: "24506B" });
  s.addText([
    { text: "그리고 위험 판정이 나오면 사람 승인 없이는 못 지나갑니다.\n", options: { bold: true, color: AMBER, breakLine: true } },
    { text: "게이트는 승인 ", options: {} },
    { text: "객체", options: { bold: true } },
    { text: "를 받지 않고 ", options: {} },
    { text: "id 문자열만", options: { bold: true } },
    { text: " 받아 원장에서 조회합니다 — 모델이 승인을 지어낼 경로가 타입 수준에 없습니다.", options: {} },
  ], {
    x: M + 0.28, y: 4.62, w: 8.5, h: 0.55, fontSize: 11.5, fontFace: B, color: "FFFFFF", lineSpacing: 16, margin: 0,
  });
}

// ══ 9. 정직성 — 측정한 것 / 모르는 것 ═══════════════════════════════════
{
  const s = slide("측정한 것과 모르는 것을 나눠 적습니다", "신뢰성");
  card(s, { x: M, y: 1.42, w: 4.35, h: 2.9, fill: "12352E" });
  s.addText("측정했습니다", { x: M + 0.25, y: 1.58, w: 3.8, h: 0.3, fontSize: 13, fontFace: B, bold: true, color: MINT, margin: 0 });
  s.addText([
    { text: "계약서 조항 존재율 — 실물 151건", options: { bullet: true, breakLine: true } },
    { text: "무역 62건 · 국문 49건 추가 집계", options: { bullet: true, breakLine: true } },
    { text: "추출 정확도 A/C — 30건 전수", options: { bullet: true, breakLine: true } },
    { text: "탐지율·오탐률 — 150건 전수", options: { bullet: true, breakLine: true } },
    { text: "테스트 122건, 외부 API 없이 1초 미만", options: { bullet: true } },
  ], {
    x: M + 0.25, y: 1.95, w: 3.85, h: 2.2, fontSize: 11.5, fontFace: B, color: "FFFFFF", lineSpacing: 20, margin: 0,
  });

  card(s, { x: 5.2, y: 1.42, w: 4.25, h: 2.9, fill: "3A2320" });
  s.addText("모릅니다", { x: 5.45, y: 1.58, w: 3.8, h: 0.3, fontSize: 13, fontFace: B, bold: true, color: BRICK, margin: 0 });
  s.addText([
    { text: "실제 사기 탐지 성능 — 자체 시나리오입니다", options: { bullet: true, breakLine: true } },
    { text: "국문 실물 계약서 조항 존재율 — 표본 0건", options: { bullet: true, breakLine: true } },
    { text: "실제 은행 트래픽의 오탐률", options: { bullet: true, breakLine: true } },
    { text: "위조 수정합의서는 못 막습니다", options: { bullet: true, breakLine: true } },
    { text: "계약서 이메일 기재율 — 국문 0.0%", options: { bullet: true } },
  ], {
    x: 5.45, y: 1.95, w: 3.75, h: 2.2, fontSize: 11.5, fontFace: B, color: "FFFFFF", lineSpacing: 20, margin: 0,
  });

  s.addText("자체 측정이 틀렸던 경위까지 기록했습니다 — 라벨 8건을 사후 정정했고 그 과정을 문서에 남겼습니다.", {
    x: M, y: 4.5, w: 8.9, h: 0.4, fontSize: 12, fontFace: B, color: AMBER, margin: 0,
  });
}

// ══ 10. 구현 현황 + 계획 (개발계획 15 · 실현가능성 15) ═══════════════════
{
  const s = slide("지금 동작하는 것과, 본선까지 만들 것", "개발 계획 · 실현 가능성");
  const done = [
    "L1 계약서 판독 — 정규식·LLM 2종",
    "L2 대조 신호 S9·S10·S11·S12·S16",
    "L4 규칙 테이블 11개 + 도달성 검사",
    "승인 게이트 + 원장 — 1회용·건·계좌 결박·TTL",
    "인젝션 3중 방어 · 근거 원문 대조",
  ];
  const todo = [
    "L3 보조 신호 LLM 축 (M6·M7·M8)",
    "L5 근거 서술 (현재는 결정론 문장)",
    "송금 신청 화면 시뮬레이터",
    "무역·국문 실물 표본 확대",
  ];
  card(s, { x: M, y: 1.42, w: 4.35, h: 2.3, fill: "12352E" });
  s.addText("예선 제출 시점 — 동작합니다", { x: M + 0.25, y: 1.56, w: 3.8, h: 0.3, fontSize: 12, fontFace: B, bold: true, color: MINT, margin: 0 });
  s.addText(done.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < done.length - 1 } })), {
    x: M + 0.25, y: 1.92, w: 3.85, h: 1.7, fontSize: 11.5, fontFace: B, color: "FFFFFF", lineSpacing: 19, margin: 0,
  });

  card(s, { x: 5.2, y: 1.42, w: 4.25, h: 2.3, fill: INK_2 });
  s.addText("본선까지 (2026-09-02)", { x: 5.45, y: 1.56, w: 3.8, h: 0.3, fontSize: 12, fontFace: B, bold: true, color: AMBER, margin: 0 });
  s.addText(todo.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < todo.length - 1 } })), {
    x: 5.45, y: 1.92, w: 3.75, h: 1.7, fontSize: 11.5, fontFace: B, color: "FFFFFF", lineSpacing: 19, margin: 0,
  });

  card(s, { x: M, y: 3.92, w: W - M * 2, h: 1.0, fill: "24506B" });
  s.addText([
    { text: "실현 가능성의 근거 — 외부 의존이 없습니다.\n", options: { bold: true, color: AMBER, breakLine: true } },
    { text: "법정 제출 서류만 사용해 은행 내부 API 의존 0 · 코어는 표준 라이브러리만 · 테스트 122건이 API 키 없이 완주합니다.", options: {} },
  ], {
    x: M + 0.28, y: 4.08, w: 8.5, h: 0.7, fontSize: 12, fontFace: B, color: "FFFFFF", lineSpacing: 18, margin: 0,
  });
}

// ══ 11. 마무리 ══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.12, h: HT, fill: { color: AMBER } });
  s.addText("한 줄로", {
    x: M, y: 1.15, w: 8.9, h: 0.3, fontSize: 12, fontFace: B, bold: true, color: AMBER, charSpacing: 2, margin: 0,
  });
  s.addText([
    { text: "계좌번호는 사기범이 바꿀 수 있습니다.\n", options: { breakLine: true } },
    { text: "3년 전 계약서의 ", options: {} },
    { text: '"변경은 서면으로"', options: { bold: true, color: AMBER } },
    { text: "는 못 바꿉니다.", options: {} },
  ], {
    x: M, y: 1.65, w: 8.9, h: 1.3, fontSize: 30, fontFace: H, bold: true,
    color: "FFFFFF", lineSpacing: 42, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: M, y: 3.15, w: 2.2, h: 0.03, fill: { color: AMBER } });
  s.addText("은행은 이미 그 계약서를 받고 있습니다. 읽기만 하면 됩니다.", {
    x: M, y: 3.45, w: 8.9, h: 0.4, fontSize: 15, fontFace: B, color: PAPER, margin: 0,
  });
  s.addText([
    { text: "KB Payee Guard", options: { bold: true, color: "FFFFFF" } },
    { text: "   ·   제8회 KB A.I Challenge 예선   ·   금융 자유주제", options: { color: MUTED } },
  ], {
    x: M, y: 4.7, w: 8.9, h: 0.35, fontSize: 12, fontFace: B, margin: 0,
  });
}

pres.writeFile({ fileName: "submission/기술설명서_KB_Payee_Guard.pptx" })
  .then((f) => console.log("생성:", f));
