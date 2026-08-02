"""End-to-end 시나리오 회귀 테스트.

여기 고정하는 것은 **e2e 측정이 실제로 찾아낸 설계 결함 1건**과, 숨기지 않기로 한
**알려진 사각지대 1건**이다. 둘 다 산문이 아니라 실행되는 코드로 남긴다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard import rules, scenarios  # noqa: E402
from kb_payee_guard.models import ContractFacts, PaymentTerms, Verdict  # noqa: E402


def _facts(requires_written: bool = True) -> ContractFacts:
    return ContractFacts(
        counterparty_name="BAUER GmbH",
        counterparty_country="DE",
        registered_contact=["hans@bauer-gmbh.de"],
        payment_terms=PaymentTerms.TT,
        amendment_clause="§14 …" if requires_written else None,
        amendment_clause_requires_written=requires_written,
    )


def _by_kind(facts: ContractFacts) -> dict[str, scenarios.Scenario]:
    return {s.kind: s for s in scenarios.build(facts, "T-1")}


class TestLegitimateChangeIsNotBlocked(unittest.TestCase):
    """🔴 e2e 가 찾은 결함 — 구 R10 은 S1(신규 계좌)만으로 HOLD 를 냈다.

    그 결과 **수정 합의서를 갖춘 정당한 계좌 변경이 100% 차단**됐고 오탐률이 50%였다.
    기술명세서 §4.3 은 "S1 은 트리거일 뿐 판별자가 아니다 — 정상 변경도 이력이 없다"고
    적어두었는데 규칙이 그 원칙을 어기고 있었다. 산문이 코드를 감시하지 못한 자리다.
    """

    def test_amendment_backed_change_passes(self):
        sc = _by_kind(_facts())["normal_legit_change"]
        d = rules.evaluate(_facts(), sc.request)
        self.assertNotIn(d.verdict, scenarios.BLOCKING,
                         f"정당한 계좌 변경이 {d.verdict.value}({d.rule_id})로 막혔다")

    def test_as_contracted_passes(self):
        sc = _by_kind(_facts())["normal_as_contracted"]
        self.assertIs(rules.evaluate(_facts(), sc.request).verdict, Verdict.PASS)

    def test_new_account_alone_never_blocks(self):
        """S1 단독 차단 금지 — 이 명제가 깨지면 오탐률이 즉시 되돌아간다."""
        for rid in rules.RULE_IDS:
            self.assertNotEqual(rid, "R10", "S1 단독 차단 규칙(R10)이 되살아났다")


class TestAttacksAreBlocked(unittest.TestCase):
    def test_most_common_bec_is_blocked(self):
        """최빈 BEC — 국가·이름·결제조건 동일, 계좌만 교체. S16 만이 잡을 수 있다."""
        sc = _by_kind(_facts())["attack_same_country_swap"]
        d = rules.evaluate(_facts(), sc.request)
        self.assertIn(d.verdict, scenarios.BLOCKING)

    def test_country_hop_is_blocked(self):
        sc = _by_kind(_facts())["attack_country_hop"]
        self.assertIn(rules.evaluate(_facts(), sc.request).verdict, scenarios.BLOCKING)


class TestKnownBlindSpot(unittest.TestCase):
    """🔴 위조 수정합의서는 **통과한다**. 이것을 테스트로 못박아 둔다.

    S16 은 지시가 어떤 **경로**로 왔는지를 보지 문서의 **진위**를 보지 않는다.
    위조 합의서는 정당한 변경과 입력이 완전히 동일하다.

    이 테스트가 "통과함"을 단언하는 이유: 나중에 누군가 이 구멍을 막았다면
    테스트가 깨지면서 **문서(README·05)의 한계 기재도 같이 고치라고** 알려준다.
    한계를 코드가 아니라 산문에만 적어두면 고쳐진 뒤에도 낡은 채로 남는다.
    """

    def test_forged_amendment_currently_passes(self):
        sc = _by_kind(_facts())["attack_forged_amendment"]
        d = rules.evaluate(_facts(), sc.request)
        self.assertTrue(sc.expect_block, "이 시나리오는 '막아야 하는데 못 막는' 케이스여야 한다")
        self.assertNotIn(
            d.verdict, scenarios.BLOCKING,
            "위조 합의서를 막게 됐다면 README·docs/05 의 '알려진 한계' 기재를 함께 갱신하라",
        )


class TestScenarioSetShape(unittest.TestCase):
    def test_has_both_normal_and_attack(self):
        """정상 시나리오가 없으면 오탐률을 못 잰다 — 전부 차단해도 탐지율 100%가 나온다."""
        scs = scenarios.build(_facts(), "T-1")
        self.assertTrue(any(s.is_attack() for s in scs))
        self.assertTrue(any(not s.is_attack() for s in scs))

    def test_scenarios_use_real_contract_facts(self):
        """계약서를 합성하지 않는다 — 송금 신청만 바꾼다."""
        f = _facts()
        for s in scenarios.build(f, "T-1"):
            self.assertEqual(s.request.payee_name, f.counterparty_name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
