"""AI 필연성 — 재현 가능한 반례.

이 파일이 증명하려는 명제는 하나다:

    "계약서에서 §Amendment 조항을 찾는 것"은 정규식으로 된다.
    "그 조항이 이메일 계좌 지시를 허용하는가"는 정규식으로 안 된다.

두 계약서는 계좌 변경에 대해 **정반대 규칙**을 갖는데, 둘 다 'in writing'을
포함한다. 한쪽에서는 요구조건이고 다른 쪽에서는 선택지 중 하나이기 때문이다.
키워드는 이 차이를 볼 수 없다.

🔴 이 테스트가 깨지면(= A가 두 계약서를 구별하면) AI 필연성 논증이 약해진다.
   그때는 논증을 고치는 게 아니라 후보를 재검토하는 것이 옳다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard.evaluate import allowed_paths  # noqa: E402
from kb_payee_guard.extract import RegexExtractor  # noqa: E402
from kb_payee_guard.models import (  # noqa: E402
    Account,
    AccountInstruction,
    ContractFacts,
    InstructionSource,
    Money,
    PaymentTerms,
    RemittanceRequest,
    Verdict,
)
from kb_payee_guard import rules  # noqa: E402

_HEAD = """SUPPLY AGREEMENT
between BAUER GmbH, Stuttgart, Germany ("Seller")
and HANMI Auto Parts Co., Ltd., Busan, Korea ("Buyer")

§13 Notices. All notices under this Agreement shall be sent to hans@bauer-gmbh.de.
"""

_TAIL = "\n§20 Payment. Irrevocable Letter of Credit at sight.\n"

# 계좌 변경을 서면 합의로 제한한다 → 이메일 지시는 위반
CONTRACT_STRICT = _HEAD + """
§14 Amendment. Any amendment to this Agreement, including any change of the
banking details set out herein, shall be in writing signed by both parties.
""" + _TAIL

# 계좌 변경을 이메일로 허용한다 → 이메일 지시가 정당
CONTRACT_LOOSE = _HEAD + """
§14 Amendment. Either party may update its banking details by notifying the
other party in writing or by email to the address set out above.
""" + _TAIL


def _gold_strict() -> ContractFacts:
    return ContractFacts(
        counterparty_name="BAUER GmbH", counterparty_country="DE",
        payment_terms=PaymentTerms.LC,
        registered_contact=["hans@bauer-gmbh.de"],
        notice_channels=["hans@bauer-gmbh.de"],
        amendment_clause_requires_written=True,
    )


def _gold_loose() -> ContractFacts:
    return ContractFacts(
        counterparty_name="BAUER GmbH", counterparty_country="DE",
        payment_terms=PaymentTerms.LC,
        registered_contact=["hans@bauer-gmbh.de"],
        notice_channels=["hans@bauer-gmbh.de"],
        amendment_clause_requires_written=False,   # ← 유일한 차이
    )


def _email_request(sender: str = "hans@bauer-gmbh.de") -> RemittanceRequest:
    return RemittanceRequest(
        case_id="AI-NEC-1",
        payee_name="BAUER GmbH",
        new_account=Account("DE99999999999999999999", "COBADEFFXXX"),
        amount=Money(120_000, "EUR"),
        remittance_type=PaymentTerms.LC,
        account_instruction=AccountInstruction(InstructionSource.EMAIL, sender),
    )


class TestGoldTruthsDiffer(unittest.TestCase):
    """전제 확인 — 두 계약서는 실제로 다른 판정을 내야 한다.
    이게 같으면 아래 테스트 전체가 무의미하다."""

    def test_allowed_path_sets_differ(self):
        self.assertNotEqual(allowed_paths(_gold_strict()), allowed_paths(_gold_loose()))

    def test_verdicts_differ(self):
        req = _email_request()
        self.assertIs(rules.evaluate(_gold_strict(), req).verdict, Verdict.BLOCK_PENDING)
        self.assertIs(rules.evaluate(_gold_loose(), req).verdict, Verdict.HOLD)


class TestRegexBaselineCannotDistinguish(unittest.TestCase):
    """🎯 본론 — A는 두 계약서를 구별하지 못한다."""

    def setUp(self):
        self.a = RegexExtractor()
        self.strict = self.a.extract(CONTRACT_STRICT)
        self.loose = self.a.extract(CONTRACT_LOOSE)

    def test_a_finds_the_clause_in_both(self):
        """조항을 '찾는' 것은 A도 한다 — 여기가 문제가 아님을 먼저 못박는다."""
        self.assertIsNotNone(self.strict.amendment_clause)
        self.assertIsNotNone(self.loose.amendment_clause)

    def test_a_extracts_payment_terms_correctly(self):
        """구조화된 항목은 A도 잘 뽑는다 — A가 전면적으로 무능한 게 아니다."""
        self.assertIs(self.strict.payment_terms, PaymentTerms.LC)
        self.assertIs(self.loose.payment_terms, PaymentTerms.LC)

    def test_a_collapses_the_distinction_that_matters(self):
        """🔴 그러나 판정을 가르는 단 하나의 비트에서 무너진다."""
        self.assertEqual(
            self.strict.amendment_clause_requires_written,
            self.loose.amendment_clause_requires_written,
            "A가 두 조항을 구별했다면 AI 필연성 논증을 재검토해야 한다",
        )

    def test_a_produces_identical_allowed_paths(self):
        self.assertEqual(allowed_paths(self.strict), allowed_paths(self.loose))

    def test_a_gets_one_of_the_two_verdicts_wrong(self):
        """A를 쓰면 두 계약서 중 하나는 반드시 틀린다 — 같은 답을 내기 때문이다."""
        req = _email_request()
        got_strict = rules.evaluate(self.strict, req).verdict
        got_loose = rules.evaluate(self.loose, req).verdict
        self.assertEqual(got_strict, got_loose)

        gold_strict = rules.evaluate(_gold_strict(), req).verdict
        gold_loose = rules.evaluate(_gold_loose(), req).verdict
        wrong = (got_strict != gold_strict) + (got_loose != gold_loose)
        self.assertGreaterEqual(wrong, 1, "A가 둘 다 맞혔다면 논증이 성립하지 않는다")


class TestWhatCMustDo(unittest.TestCase):
    """C(LLM 추출기)의 합격 조건을 코드로 고정한다.
    C를 붙이면 이 테스트가 그대로 C의 인수 기준이 된다."""

    def test_gold_facts_pass_the_bar(self):
        """정답 추출이면 두 계약서의 경로 집합이 갈린다 — C가 도달해야 할 지점."""
        s, l = allowed_paths(_gold_strict()), allowed_paths(_gold_loose())
        self.assertIn(InstructionSource.EMAIL, l)
        self.assertNotIn(InstructionSource.EMAIL, s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
