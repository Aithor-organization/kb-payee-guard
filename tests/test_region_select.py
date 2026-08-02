"""후보 구간 선별 회귀 테스트.

이 모듈이 깨지면 C 의 recall 이 조용히 떨어진다 — 조항이 발췌문에서 빠져도
LLM 은 에러를 내지 않고 그냥 "조항 없음"을 반환하기 때문이다.
실측(2026-08-02): 구간 선별 도입 전 recall 66.7% → 도입 후 91.7%.

여기 고정하는 것은 **세 가지 실제 버그**다. 전부 구현 중에 발생시켜 확인했다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard.llm_extract import _P1_PROCEDURE, select_regions  # noqa: E402

_FILLER = "이 문단은 무관한 채움 텍스트입니다. " * 200          # ≈ 4.4K chars
_CLAUSE = "This Agreement may be modified only in writing signed by an officer of each party."


class TestShortDocsPassThrough(unittest.TestCase):
    def test_under_budget_returns_original(self):
        t = "짧은 계약서 " + _CLAUSE
        self.assertEqual(select_regions(t, budget=24_000), t)


class TestClauseSurvivesTruncation(unittest.TestCase):
    """🔴 버그 1 — 전문을 상한까지 자르면 문서 뒤쪽 조항이 통째로 날아간다.

    실측: 놓친 8건 중 4건이 60K 상한을 넘는 문서였고(86K·68K·106K·91K),
    조항은 문서 80~97% 지점에 있었다. 계약서는 변경조항을 끝에 둔다.
    """

    def test_clause_at_document_end_is_kept(self):
        t = _FILLER * 12 + _CLAUSE          # ≈ 53K, 조항이 맨 끝
        out = select_regions(t, budget=12_000)
        self.assertLess(len(out), 14_000, "예산을 지켜야 한다")
        self.assertIn(_CLAUSE, out, "문서 끝의 변경조항이 발췌문에 남아야 한다")

    def test_head_is_kept_for_parties(self):
        """당사자·소재국은 서두에 있다 — 조항만 챙기고 서두를 버리면 S9/S11 이 죽는다."""
        head = "SUPPLY AGREEMENT between BAUER GmbH, Stuttgart, Germany and HANMI Co."
        t = head + _FILLER * 12 + _CLAUSE
        out = select_regions(t, budget=12_000)
        self.assertIn("BAUER GmbH", out)


class TestOverlappingWindowsAreMerged(unittest.TestCase):
    """🔴 버그 2 — 겹치는 구간을 skip 하면 뒤 창 안의 조항까지 사라진다.

    실측(cuad-021): 매치가 22977·23973 두 개였고 창이 겹쳤다. 뒤 창을 skip 하자
    앞 창이 23727 에서 끝나 조항(23988)이 잘렸다. 겹침은 중복이 아니라 **연속**이다.
    """

    def test_two_nearby_matches_keep_the_later_clause(self):
        decoy = "Notwithstanding any modification of the foregoing schedule, "
        t = _FILLER * 12 + decoy + "x" * 900 + _CLAUSE
        out = select_regions(t, budget=12_000)
        self.assertIn(_CLAUSE, out, "앞 매치와 겹친다는 이유로 뒤 조항이 사라지면 안 된다")


class TestPriorityBeatsDocumentOrder(unittest.TestCase):
    """🔴 버그 3 — 앞에서부터 담으면 서두의 무관한 'amendment' 언급이 예산을 먹는다.

    실측: 상한 12개를 문서 앞쪽 매치가 채워 문서 후반의 진짜 조항이 탈락했다(3건).
    """

    def test_many_early_mentions_do_not_starve_the_real_clause(self):
        noise = "The parties discussed an amendment to the schedule. " * 40
        t = noise + _FILLER * 12 + _CLAUSE
        out = select_regions(t, budget=12_000)
        self.assertIn(_CLAUSE, out)


class TestOutputIsSubsetOfOriginal(unittest.TestCase):
    """발췌문이 원문 부분집합이어야 `_verify_spans` 의 원문 대조가 성립한다.
    구분자를 원문에 없는 문자열로 둔 이유이기도 하다."""

    def test_every_chunk_exists_in_source(self):
        t = _FILLER * 12 + _CLAUSE
        out = select_regions(t, budget=12_000)
        for chunk in out.split("\n[…]\n"):
            self.assertIn(chunk, t, "발췌 조각은 원문에 그대로 있어야 한다")


class TestProcedurePattern(unittest.TestCase):
    """P1 은 '계약 자체의 변경 절차' 문장을 잡아야 한다."""

    def test_matches_common_forms(self):
        for s in (
            "No modification, amendment, or waiver of any provision shall be effective",
            "This Agreement may not be amended except by an instrument in writing",
            "This Agreement may be modified only in writing signed by an officer",
            "Any amendment or modification of this Agreement must be made in writing",
            "may be amended only by a written instrument executed by the Parties",
        ):
            self.assertIsNotNone(_P1_PROCEDURE.search(s), f"놓침: {s}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
