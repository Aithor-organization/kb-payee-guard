"""국문 계약서 처리 회귀 테스트.

## 왜 별도 파일인가

코퍼스가 CUAD·SEC(미국 상용계약)뿐이라 국문 처리는 **한 번도 실행된 적이 없었다**.
표본이 들어오고 나서 안 되는 걸 발견하면 그때는 고칠 시간이 없다.
표본보다 먼저 이 테스트를 둔다.

🔴 A(정규식)를 국문에서도 동작하게 만드는 것이 중요하다. A 는 C 와 비교되는 **baseline** 이라,
언어 때문에 A 가 0점이 되면 "AI 가 낫다"는 비교 자체가 무의미해진다. 공정한 대조군을 만든다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard.extract import RegexExtractor  # noqa: E402
from kb_payee_guard.llm_extract import _P1_PROCEDURE, select_regions  # noqa: E402
from kb_payee_guard.models import PaymentTerms  # noqa: E402

CONTRACT_KR = """물품공급계약서

주식회사 바우어코리아(이하 "공급자")와 한미자동차부품 주식회사(이하 "구매자")는
다음과 같이 물품공급계약을 체결한다.

제3조 (대금지급)
구매자는 물품대금을 취소불능 화환신용장(Irrevocable L/C) 방식으로 지급한다.

제12조 (통지)
본 계약에 관한 통지는 아래 주소 및 전자우편으로 한다.
  공급자: hans@bauer-korea.co.kr

제14조 (계약의 변경)
본 계약의 내용을 변경하고자 하는 경우에는 양 당사자의 서면 합의에 의하여야 한다.
"""

_FILLER_KR = "제9조 (품질보증) 공급자는 물품의 품질을 보증한다. " * 400


class TestKoreanClauseHeadings(unittest.TestCase):
    """🔴 국문 조항 제목은 `제14조 (계약의 변경)` — 번호와 키워드 사이에 `조`와 괄호 제목이 낀다.

    영문용 패턴(번호 직후 키워드)으로는 못 잡는다. 실측에서 전건 실패했다.
    """

    def setUp(self):
        self.f = RegexExtractor().extract(CONTRACT_KR)

    def test_amendment_clause_is_found(self):
        self.assertIsNotNone(self.f.amendment_clause, "국문 변경조항을 못 찾았다")

    def test_written_requirement_is_detected(self):
        self.assertTrue(self.f.amendment_clause_requires_written,
                        "'서면 합의에 의하여야 한다'를 서면 요구로 읽어야 한다")

    def test_notice_clause_is_found(self):
        self.assertIsNotNone(self.f.notice_clause)

    def test_email_is_extracted(self):
        self.assertIn("hans@bauer-korea.co.kr", self.f.registered_contact)


class TestKoreanPaymentTerms(unittest.TestCase):
    def test_letter_of_credit(self):
        self.assertIs(RegexExtractor().extract(CONTRACT_KR).payment_terms, PaymentTerms.LC)

    def test_korean_only_forms(self):
        """영문 병기 없이 국문만 있어도 잡아야 한다 — 실제 국문 계약서가 그렇다."""
        cases = {
            "대금은 전신환송금 방식으로 지급한다.": PaymentTerms.TT,
            "결제는 인수인도 조건으로 한다.": PaymentTerms.DA,
            "지급인도 조건에 따라 서류를 인도한다.": PaymentTerms.DP,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertIs(RegexExtractor().extract(text).payment_terms, expected)


class TestKoreanRegionSelection(unittest.TestCase):
    """긴 국문 계약서에서 변경조항이 발췌문에 남아야 한다.

    남지 않으면 C 는 '조항 없음'을 반환하고 **에러 없이 조용히** recall 이 떨어진다.
    """

    def setUp(self):
        self.long_kr = (CONTRACT_KR.split("제12조")[0] + _FILLER_KR
                        + "제12조" + CONTRACT_KR.split("제12조")[1])

    def test_p1_matches_korean_amendment(self):
        self.assertIsNotNone(_P1_PROCEDURE.search(CONTRACT_KR))

    def test_clause_survives_long_document(self):
        out = select_regions(self.long_kr, budget=6_000)
        self.assertLess(len(out), 8_000)
        self.assertIn("서면 합의에 의하여야", out, "국문 변경조항이 발췌문에서 잘렸다")

    def test_notice_contact_survives(self):
        out = select_regions(self.long_kr, budget=6_000)
        self.assertIn("hans@bauer-korea.co.kr", out)


class TestNoOvermatching(unittest.TestCase):
    """🔴 국문 '변경'은 물량·사양 변경에도 쓰인다. 계약 자체의 변경만 잡아야 한다.

    과잉매칭하면 오탐이 늘고, 그건 e2e 오탐률로 되돌아온다.
    """

    def test_product_spec_change_is_not_an_amendment_clause(self):
        for text in (
            "제7조 (사양변경) 구매자는 물품의 사양을 변경할 수 있다.",
            "납품 수량의 변경은 발주서로 갈음한다.",
            "공급자는 주소 변경 시 즉시 통보한다.",
        ):
            with self.subTest(text=text):
                f = RegexExtractor().extract(text)
                self.assertFalse(
                    f.amendment_clause_requires_written,
                    f"계약 변경 조항이 아닌데 서면요구로 판정: {text}",
                )


class TestEnglishStillWorks(unittest.TestCase):
    """국문 패턴 추가가 영문을 깨뜨리지 않았는지 — 같은 정규식을 공유한다."""

    def test_english_amendment_still_detected(self):
        en = ("SUPPLY AGREEMENT\n\n"
              "14. Amendment\n"
              "No modification of this Agreement shall be effective unless in writing "
              "signed by both parties.\n")
        f = RegexExtractor().extract(en)
        self.assertIsNotNone(f.amendment_clause)
        self.assertTrue(f.amendment_clause_requires_written)


if __name__ == "__main__":
    unittest.main(verbosity=2)
