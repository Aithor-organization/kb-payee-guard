#!/usr/bin/env python3.12
"""제출 zip 조립 — 제8회 KB A.I Challenge 예선

    python3.12 submission/build_zip.py

공고 요건 (docs/_scout-contest.md 실측):
  · 참가신청서 + 기술설명서(PDF·PPT) + 프로토타입(개발 코드)을 **하나의 zip**으로
  · 최대 3GB · 확장자 .zip 강제 · zip 내부 폴더 구조 규정 없음
  · 마감 2026-08-03(월) 16:00 — 마감 후 서버단 차단, 우회 불가

🔴 GitHub 링크로 제출하면 "참가접수기간 이후 수정·변경 이력 확인 시 심사 대상 제외"다.
   그래서 **코드 스냅샷을 zip에 동봉**한다. 링크를 병기하더라도 마감 후 레포를 동결할 것.

🔴 왜 shell `zip` 이 아니라 Python 인가 (2026-08-02 실측):
   macOS 의 `zip` 은 UTF-8 파일명을 쓰면서 **general purpose bit 11(UTF-8 flag)을 세우지 않는다.**
   그 결과 `기술설명서_….pptx` 가 `Ω╕░∞êá∞äñδ¬à∞ä£_….pptx` 로 깨져 보였다.
   심사자가 압축을 풀었을 때 파일명이 깨지는 것은 그 자체로 감점 요인이다.
   Python `zipfile` 은 비-ASCII 이름에 이 플래그를 자동으로 세운다.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
import pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission" / "dist"
STAGE = OUT / "KB_Payee_Guard"
ZIP = OUT / "KB_Payee_Guard_제출.zip"
DECK = ROOT / "submission" / "기술설명서_KB_Payee_Guard.pptx"

# 🔴 서명한 필수서류(PDF)를 **어디서** 가져오는가 (2026-08-03 수정).
#
#    이전 설계는 "STAGE/필수서류/ 에 넣고 다시 실행하세요" 였는데, main() 이 매 실행마다
#    `shutil.rmtree(STAGE)` 로 그 폴더를 **지우고 시작**한다. 넣어도 다음 실행에서 사라지는
#    catch-22 였고, 실제로 생성 ZIP 에 PDF 가 0건이었다.
#    → 지워지지 않는 별도 입력 디렉터리에서 읽는다. 환경변수로 덮어쓸 수 있다.
#
#    ⚠️ 서명본에는 개인정보가 있다. 이 디렉터리는 .gitignore 에 있으며 커밋하지 않는다.
DOCS_SRC = pathlib.Path(os.environ.get("KB_DOCS_DIR") or (ROOT / "submission" / "_필수서류_원본"))

# 🔴 재배포 금지·비밀·파생물 — 스테이징에서 제거한다 (git 추적 여부와 무관하게 이중 차단)
EXCLUDE_NAMES = {".env", ".DS_Store"}
EXCLUDE_DIRS = {"__pycache__", "_restricted", "_raw", ".git", "node_modules"}
EXCLUDE_GLOBS = ("itc-*.txt", "_scout-*.md", "*.pyc")


def prune(base: Path) -> None:
    for d in list(base.rglob("*")):
        if d.is_dir() and d.name in EXCLUDE_DIRS:
            shutil.rmtree(d, ignore_errors=True)
    for f in list(base.rglob("*")):
        if f.is_file() and (f.name in EXCLUDE_NAMES
                            or any(f.match(g) for g in EXCLUDE_GLOBS)):
            f.unlink(missing_ok=True)


def main() -> int:
    if not DECK.is_file():
        print("❌ 기술설명서가 없습니다. 먼저: node submission/build_deck.js", file=sys.stderr)
        return 1

    shutil.rmtree(STAGE, ignore_errors=True)
    ZIP.unlink(missing_ok=True)
    STAGE.mkdir(parents=True)

    # 1. 기술설명서
    shutil.copy2(DECK, STAGE / DECK.name)

    # 2. 프로토타입 (코드 스냅샷)
    proto = STAGE / "prototype"
    proto.mkdir()
    for d in ("src", "tests", "scripts", "workflows", "compliance_packs", "docs"):
        src = ROOT / d
        if src.is_dir():
            shutil.copytree(src, proto / d)
    for f in ("README.md",):
        if (ROOT / f).is_file():
            shutil.copy2(ROOT / f, proto / f)

    # 3. 평가 재현용 데이터 — 라이선스 확인된 산출물만 (원문 코퍼스는 넣지 않는다)
    dc = proto / "data" / "contracts"
    dc.mkdir(parents=True)
    # 🔴 `_e2e_result.json` 은 2026-08-03 에 (코퍼스 × 추출기)별로 분리됐다.
    #    옛 이름만 복사하면 ZIP 에서 E2E 원자료가 통째로 빠진다 — 실제로 그랬다.
    for f in ("MANIFEST.md", "_gold.json", "_baseline_result.json", "_corpus_manifest.json",
              "_e2e_result_gold.json", "_e2e_result_A.json", "_e2e_result_C.json",
              "_e2e_holdout_A.json", "_e2e_holdout_C.json", "_detect.json",
              "detect_clauses.py", "detect_clauses_kr.py"):
        p = ROOT / "data" / "contracts" / f
        if p.is_file():
            shutil.copy2(p, dc / f)

    prune(STAGE)

    # 4. 필수서류 — 지워지지 않는 입력 디렉터리에서 복사한다
    docs_dir = STAGE / "필수서류"
    docs_dir.mkdir()
    copied = []
    if DOCS_SRC.is_dir():
        for pdf in sorted(DOCS_SRC.glob("*.pdf")):
            shutil.copy2(pdf, docs_dir / pdf.name)
            copied.append(pdf.name)
    if copied:
        print(f"  필수서류 {len(copied)}건 복사 ({DOCS_SRC})")
        for n in copied:
            print(f"    · {n}")
    else:
        print(f"  ⚠️  필수서류 0건 — {DOCS_SRC} 에 서명본 PDF 를 넣으십시오"
              f" (또는 KB_DOCS_DIR 환경변수로 경로 지정)")
    (docs_dir / "_여기에_넣으세요.txt").write_text(
        "아래 3건을 **submission/_필수서류_원본/** 에 넣고 다시 실행하세요\n"
        "(python3.12 submission/build_zip.py · 다른 경로면 KB_DOCS_DIR 환경변수).\n"
        "🔴 이 폴더는 매 실행마다 삭제되므로 여기 넣으면 사라집니다.\n\n"
        "  1. 제8회 Future Finance AI Challenge 참가신청서.pdf   (작성 + 서명)\n"
        "  2. 제8회 Future Finance AI Challenge 서약서.pdf        (서명/날인)\n"
        "  3. [필수]개인정보 수집·이용 동의서.pdf                  (서명/날인)\n\n"
        "🔴 서약서·개인정보동의서는 **팀원 개인별** 작성입니다. 팀장 1부만 내면 서류 미비입니다.\n"
        "🔴 참가신청서 §3 'AI 활용 내용' 7칸(아이디어 발굴/정보수집/데이터 분석/\n"
        "   코드작성·디버깅/문서작성/이미지 제작/발표자료)에 사용 모델과 반영 정도를\n"
        "   기재해야 합니다. AI 사용은 금지가 아니라 **신고 대상**입니다.\n\n"
        "양식: https://kb-aichallenge.com/kb_aichallenge_docs.zip\n",
        encoding="utf-8")

    # 5. 안내문
    (STAGE / "README_제출물.md").write_text(f"""# KB Payee Guard — 제8회 KB A.I Challenge 예선 제출물

| 항목 | 위치 |
|---|---|
| 기술설명서 | `{DECK.name}` |
| 프로토타입 (구현 코드) | `prototype/` |
| 참가신청서·서약서·동의서 | `필수서류/` |

## 프로토타입 재현

```bash
cd prototype
python3.12 -m unittest discover -s tests      # 128 tests · 외부 API 키 불필요 · 약 0.2초
python3.12 scripts/run_baselines.py --with-c  # 추출 정확도 A/C (OpenAI 호출)
python3.12 scripts/run_e2e.py --extract C     # 탐지율·오탐률 (OpenAI 호출)
```

API 키 없이도 **테스트 128건 전부**가 통과합니다. 판정 엔진이 결정론이기 때문입니다.

## 측정 결과 요약

| | 정규식 추출 | LLM 추출 |
|---|--:|--:|
| 계약 조항 추출 정확도 | 30.0% | **90.0%** |
| 재현율 | 20.8% | **91.7%** |
| 차단율 · 위조 제외 (합성 시나리오) | 16.7% | **93.3%** |
| 정상거래 오탐률 | 0.0% | **0.0%** |

근거·한계: `prototype/docs/03_R7_측정.md` · `05_베이스라인A_실측.md` · `06_E2E_탐지율_오탐률.md`

🔴 위 수치는 **자체 설계 시나리오** 기준이며 실제 사기 탐지 성능이 아닙니다.
   알려진 사각지대(위조 수정합의서 미탐)와 미측정 항목을 문서에 함께 적었습니다.

## 데이터 안내

`prototype/data/contracts/` 에는 **평가 산출물과 판정 코드만** 넣었습니다.
계약서 원문 코퍼스는 용량과 재배포 조건 때문에 제외했습니다 — 출처·라이선스·수집 방법은
`MANIFEST.md` 에 전부 기재돼 있어 재현할 수 있습니다.
""", encoding="utf-8")

    # 6. 압축 — Python zipfile 이 비-ASCII 이름에 UTF-8 플래그를 세운다
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(STAGE.rglob("*")):
            z.write(p, p.relative_to(STAGE.parent))

    size_mb = ZIP.stat().st_size / 1024 / 1024
    print(f"✅ {ZIP.relative_to(ROOT)}  ({size_mb:.1f} MB)")

    # 7. 제출 전 자가 점검 — zip 안의 **실제 이름**으로 검사한다
    zf = zipfile.ZipFile(ZIP)
    names = zf.namelist()
    joined = "\n".join(names)

    # 🔴 필수서류는 "PDF 가 하나라도 있는가" 로 검사하면 안 된다 (2026-08-03).
    #    빈 `only-one.pdf` 한 개만 넣어도 통과하는 fail-open 이었다. 서류 미비는 실격
    #    사유이므로, **3종 각각**의 존재 + 비어 있지 않음 + 실제 PDF 헤더까지 확인한다.
    REQUIRED_DOCS = (("참가신청서", "참가신청서"),
                     ("서약서", "서약서"),
                     ("개인정보 동의서", "개인정보"))
    doc_status: list[tuple[str, bool, str]] = []
    for label, kw in REQUIRED_DOCS:
        cand = [n for n in names
                if n.endswith(".pdf") and "필수서류" in n and kw in n]
        if not cand:
            doc_status.append((label, False, "없음")); continue
        n = cand[0]
        info = zf.getinfo(n)
        head = zf.read(n)[:5]
        if info.file_size < 1024:
            doc_status.append((label, False, f"{info.file_size}B — 비어 있거나 손상")); continue
        if head != b"%PDF-":
            doc_status.append((label, False, f"PDF 헤더 아님({head!r})")); continue
        doc_status.append((label, True, f"{info.file_size // 1024}KB"))
    for label, ok, note in doc_status:
        print(f"    {'·' if ok else '🔴'} 필수서류/{label}: {note}")

    checks = [
        ("기술설명서(pptx)", any(n.endswith(".pptx") for n in names), True),
        ("프로토타입 코드", "prototype/src/" in joined, True),
        ("테스트", "prototype/tests/" in joined, True),
        ("측정 문서", "prototype/docs/" in joined, True),
        # 🔴 서류 미비는 실격 사유다 — 경고가 아니라 차단으로 둔다.
        (f"필수서류 3종 서명본 ({sum(ok for _, ok, _ in doc_status)}/3)",
         all(ok for _, ok, _ in doc_status), True),
        ("재배포 금지 자료 없음", not any("itc-" in n or "_restricted" in n for n in names), True),
        ("비밀키 없음", not any(n.endswith(".env") for n in names), True),
        ("3GB 이하", size_mb < 3000, True),
    ]
    print("\n제출 전 점검:")
    blocking = 0
    for label, ok, required in checks:
        if ok:
            print(f"  ✅ {label}")
        elif required:
            print(f"  ❌ {label}")
            blocking += 1
        else:
            print(f"  ⚠️  {label} — 서명 후 필수서류/ 에 넣고 다시 실행하세요")

    # 파일명 인코딩 — 깨지면 심사자가 압축 해제 시 알아볼 수 없다
    bad = [n for n in names if any(ord(c) > 0x2000 and ord(c) < 0x3000 for c in n)]
    print("  ✅ 한글 파일명 정상" if not bad else f"  ❌ 파일명 깨짐: {bad[:2]}")

    print(f"\n총 {len([n for n in names if not n.endswith('/')])} 파일")
    if blocking:
        print(f"\n🔴 필수 항목 {blocking}건 누락 — 제출 불가", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
