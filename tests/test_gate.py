"""승인 게이트 공격 테스트 — 기술명세서 §11.2 T1~T5 · T10 · T11.

각 테스트가 막는 공격을 이름에 적었다. 테스트가 깨지면 그 공격이 통과한다는 뜻이다.
외부 API 불필요 — 전부 결정론이다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard.gate import (  # noqa: E402
    ApprovalError,
    ApprovalLedger,
    DEFAULT_TTL_SECONDS,
    GateResult,
    VerifyChannel,
    account_fingerprint,
    new_trace_id,
)
from kb_payee_guard.models import Account, Verdict  # noqa: E402

T0 = 1_000_000.0
ACC = Account(number="LT12 3250 0000 0000 0047")
OTHER_ACC = Account(number="DE89 3704 0044 0532 0130 00")


def _ledger_with_approval(*, case_id="REM-1", account=ACC, now=T0, ttl=DEFAULT_TTL_SECONDS):
    ledger = ApprovalLedger()
    trace = new_trace_id()
    approval = ledger.issue(
        case_id=case_id, account=account, approved_by="김담당",
        verified_via=VerifyChannel.CONTRACT_CONTACT, trace_id=trace,
        ttl_seconds=ttl, now=now,
    )
    return ledger, trace, approval


class T1_NoApprovalCannotPass(unittest.TestCase):
    """T1 — 승인 없이 게이트 통과 시도 (INV-2)."""

    def test_every_blocking_verdict_needs_approval(self):
        ledger = ApprovalLedger()
        for verdict in (Verdict.HOLD, Verdict.BLOCK_PENDING, Verdict.UNKNOWN):
            with self.subTest(verdict=verdict):
                r = ledger.gate(verdict=verdict, case_id="REM-1", account=ACC,
                                trace_id=new_trace_id(), now=T0)
                self.assertTrue(r.blocked, f"{verdict}가 승인 없이 통과했다")
                self.assertIn("승인 없이", r.reason)

    def test_pass_and_notice_do_not_call_a_human(self):
        """정상 건까지 사람을 부르면 게이트가 꺼진다 — 반대 방향 검사."""
        ledger = ApprovalLedger()
        for verdict in (Verdict.PASS, Verdict.NOTICE):
            with self.subTest(verdict=verdict):
                r = ledger.gate(verdict=verdict, case_id="REM-1", account=ACC,
                                trace_id=new_trace_id(), now=T0)
                self.assertTrue(r.allowed)


class T2_ApprovalIsSingleUse(unittest.TestCase):
    """T2 — 승인 재사용 (replay). INV-3."""

    def test_second_use_is_rejected(self):
        ledger, trace, approval = _ledger_with_approval()
        first = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                            trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        self.assertTrue(first.allowed)

        second = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                             trace_id=trace, approval_id=approval.approval_id, now=T0 + 2)
        self.assertTrue(second.blocked)
        self.assertIn("이미 사용된", second.reason)


class T3_ApprovalIsBoundToCase(unittest.TestCase):
    """T3 — 다른 건의 승인을 가져다 쓰기. INV-3."""

    def test_cross_case_reuse_is_rejected(self):
        ledger, trace, approval = _ledger_with_approval(case_id="REM-1")
        r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-2", account=ACC,
                        trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        self.assertTrue(r.blocked)
        self.assertIn("다른 건", r.reason)

    def test_unused_after_rejection(self):
        """거부된 시도가 승인을 소모하면 안 된다 — 정당한 사용까지 막힌다."""
        ledger, trace, approval = _ledger_with_approval(case_id="REM-1")
        ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-2", account=ACC,
                    trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        ok = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                         trace_id=trace, approval_id=approval.approval_id, now=T0 + 2)
        self.assertTrue(ok.allowed)


class T4_ApprovalIsBoundToAccount(unittest.TestCase):
    """T4 — 승인받은 뒤 계좌만 바꿔치기. INV-3."""

    def test_swapped_account_is_rejected(self):
        ledger, trace, approval = _ledger_with_approval(account=ACC)
        r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=OTHER_ACC,
                        trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        self.assertTrue(r.blocked)
        self.assertIn("다른 계좌", r.reason)

    def test_formatting_difference_is_not_a_swap(self):
        """공백·하이픈·대소문자는 표기 차이다. 이걸 바꿔치기로 보면 정상 건이 막힌다."""
        ledger, trace, approval = _ledger_with_approval(account=ACC)
        same = Account(number="lt12-3250-0000-0000-0047")
        r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=same,
                        trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        self.assertTrue(r.allowed, "표기만 다른 같은 계좌가 거부됐다")


class T5_ApprovalExpires(unittest.TestCase):
    """T5 — 승인을 오래 들고 있다가 나중에 사용. INV-3."""

    def test_use_after_ttl_is_rejected(self):
        ledger, trace, approval = _ledger_with_approval(ttl=300.0)
        r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                        trace_id=trace, approval_id=approval.approval_id, now=T0 + 300.0)
        self.assertTrue(r.blocked)
        self.assertIn("만료", r.reason)

    def test_use_just_before_ttl_is_allowed(self):
        ledger, trace, approval = _ledger_with_approval(ttl=300.0)
        r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                        trace_id=trace, approval_id=approval.approval_id, now=T0 + 299.9)
        self.assertTrue(r.allowed)


class T10_ModelCannotSelfApprove(unittest.TestCase):
    """T10 — 모델이 approval_id 를 지어내 게이트를 넘으려는 시도. INV-7."""

    def test_fabricated_id_is_rejected(self):
        ledger = ApprovalLedger()
        for fake in ("apv_deadbeefdeadbeefdeadbeef", "approved", "", "apv_"):
            with self.subTest(fake=fake):
                r = ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                                trace_id=new_trace_id(), approval_id=fake, now=T0)
                self.assertTrue(r.blocked, f"지어낸 승인 id '{fake}' 가 통과했다")

    def test_gate_signature_takes_an_id_not_an_object(self):
        """🔴 INV-7의 기계적 형태.

        `gate()` 가 승인 **객체**를 받으면 그럴듯한 객체를 만들어 넘기는 것이 곧 우회다.
        id 만 받고 원장이 진실의 출처여야 한다. 시그니처가 바뀌면 이 테스트가 깨진다.
        """
        import inspect
        sig = inspect.signature(ApprovalLedger.gate)
        self.assertIn("approval_id", sig.parameters)
        self.assertNotIn("approval", sig.parameters)
        self.assertEqual(sig.parameters["approval_id"].annotation, "str | None")


class T11_VerifyChannelWhitelist(unittest.TestCase):
    """T11 — 확인 채널로 요청 메일 회신·메일 기재 번호를 지정. §6.2."""

    def test_attacker_controlled_channels_are_rejected(self):
        ledger = ApprovalLedger()
        for bad in ("email_reply", "phone_in_mail", "sms", "메일회신", ""):
            with self.subTest(channel=bad):
                with self.assertRaises(ApprovalError):
                    ledger.issue(case_id="REM-1", account=ACC, approved_by="김담당",
                                 verified_via=bad, trace_id=new_trace_id(), now=T0)

    def test_whitelisted_channels_are_accepted(self):
        ledger = ApprovalLedger()
        for good in ("contract_contact", "registered_phone", "in_person"):
            with self.subTest(channel=good):
                a = ledger.issue(case_id="REM-1", account=ACC, approved_by="김담당",
                                 verified_via=good, trace_id=new_trace_id(), now=T0)
                self.assertEqual(a.verified_via.value, good)

    def test_blocked_channels_are_not_even_enum_members(self):
        """열거형에 없어야 실수로 추가되지 않는다."""
        values = {c.value for c in VerifyChannel}
        self.assertNotIn("email_reply", values)
        self.assertNotIn("phone_in_mail", values)


class IssueGuards(unittest.TestCase):
    """발급 자체가 갖춰야 할 최소 조건."""

    def test_empty_case_id_is_rejected(self):
        ledger = ApprovalLedger()
        with self.assertRaises(ApprovalError):
            ledger.issue(case_id="", account=ACC, approved_by="김담당",
                         verified_via=VerifyChannel.IN_PERSON,
                         trace_id=new_trace_id(), now=T0)

    def test_anonymous_approver_is_rejected(self):
        """누가 확인했는지 남지 않으면 분쟁 시 근거가 없다."""
        ledger = ApprovalLedger()
        with self.assertRaises(ApprovalError):
            ledger.issue(case_id="REM-1", account=ACC, approved_by="",
                         verified_via=VerifyChannel.IN_PERSON,
                         trace_id=new_trace_id(), now=T0)

    def test_raw_account_number_is_not_stored(self):
        """§7 저장 정책 — 계좌번호는 해시만 남는다."""
        _, _, approval = _ledger_with_approval()
        self.assertNotIn("3250", approval.account_fingerprint)
        self.assertTrue(approval.account_fingerprint.startswith("sha256:"))


class INV4_TraceIdPropagates(unittest.TestCase):
    """INV-4 — trace_id 가 발급·게이트·감사를 관통한다."""

    def test_trace_id_is_unique(self):
        self.assertNotEqual(new_trace_id(), new_trace_id())

    def test_events_carry_the_trace_id(self):
        ledger, trace, approval = _ledger_with_approval()
        ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                    trace_id=trace, approval_id=approval.approval_id, now=T0 + 1)
        events = ledger.events_for(trace)
        self.assertEqual([e.kind for e in events], ["issued", "allowed"])
        self.assertTrue(all(e.trace_id == trace for e in events))

    def test_gate_result_carries_the_trace_id(self):
        ledger = ApprovalLedger()
        trace = new_trace_id()
        r = ledger.gate(verdict=Verdict.HOLD, case_id="REM-1", account=ACC,
                        trace_id=trace, now=T0)
        self.assertEqual(r.trace_id, trace)

    def test_rejections_are_recorded_too(self):
        """차단이 로그에 안 남으면 공격 시도를 사후에 볼 수 없다."""
        ledger = ApprovalLedger()
        trace = new_trace_id()
        ledger.gate(verdict=Verdict.BLOCK_PENDING, case_id="REM-1", account=ACC,
                    trace_id=trace, now=T0)
        events = ledger.events_for(trace)
        self.assertEqual([e.kind for e in events], ["rejected"])

    def test_audit_log_is_append_only_from_outside(self):
        ledger, trace, _ = _ledger_with_approval()
        before = len(ledger.events)
        self.assertIsInstance(ledger.events, tuple)   # 외부에서 pop/clear 불가
        self.assertEqual(len(ledger.events), before)


class GateResultShape(unittest.TestCase):
    def test_blocked_is_the_negation_of_allowed(self):
        for allowed in (True, False):
            r = GateResult(allowed, "x", "trc_1")
            self.assertEqual(r.blocked, not allowed)


class FingerprintProperties(unittest.TestCase):
    def test_same_account_same_fingerprint(self):
        self.assertEqual(account_fingerprint(Account("LT12 3250")),
                         account_fingerprint(Account("lt12-3250")))

    def test_different_account_different_fingerprint(self):
        self.assertNotEqual(account_fingerprint(ACC), account_fingerprint(OTHER_ACC))


if __name__ == "__main__":
    unittest.main()
