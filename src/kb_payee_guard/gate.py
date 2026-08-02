"""L6 승인 게이트 + 승인 원장 (결정론).

기술명세서 §6의 코드화. stdlib only.

이 모듈이 강제하는 불변식:

🔴 INV-2  승인 없이 송금을 통과시킬 수 없다.
          HOLD / BLOCK_PENDING / UNKNOWN 은 사람 승인 없이는 ALLOWED 가 안 된다.

🔴 INV-3  승인은 1회용이고 건·계좌에 결박된다.
          consumed · case_id · account_fingerprint · TTL 네 개가 각각 다른 공격을 막는다.

🔴 INV-4  trace_id 가 판정→승인→게이트 전 구간을 관통한다.
          감사 로그는 append-only 이고 각 이벤트가 trace_id 를 달고 있다.

🔴 INV-7  모델이 스스로 만든 승인은 통과하지 못한다.
          `gate()` 는 **승인 객체를 받지 않는다.** `approval_id` 문자열만 받아
          원장에서 조회한다. 원장에 없는 id 는 존재하지 않는 승인이다.
          모델이 `RemittanceApproval(...)` 을 통째로 만들어 넘길 경로가 타입 수준에서 없다.

왜 승인 객체가 아니라 id 인가 — 이것이 이 파일의 핵심 설계다.
승인 객체를 인자로 받으면 "그럴듯한 객체를 만들어 넘기는 것"이 곧 우회다.
id 만 받고 원장이 진실의 출처가 되면, 우회하려면 원장에 쓰는 수밖에 없고
원장에 쓰는 유일한 경로는 `issue()` 이며 그것은 사람 확인 채널을 요구한다.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum

from .models import Account, Verdict


class VerifyChannel(str, Enum):
    """확인 채널 화이트리스트 (기술명세서 §6.2).

    🔴 여기 없는 채널은 값 자체가 존재하지 않는다.
       `email_reply`(요청 메일 회신)와 `phone_in_mail`(메일에 적힌 번호)은
       **사기범이 받는 쪽**이라 확인이 되지 않는다. 화이트리스트가 아니라
       열거형에서 아예 빼는 것이 옳다 — 실수로 추가할 수 없게.
    """

    CONTRACT_CONTACT = "contract_contact"   # 🎯 계약서 기재 연락처 — 체결 시점 확정, 사후 변경 불가
    REGISTERED_PHONE = "registered_phone"   # 은행 등록 연락처
    IN_PERSON = "in_person"                 # 대면


#: 승인이 필요한 등급. PASS·NOTICE 는 사람을 부르지 않는다.
_NEEDS_APPROVAL = frozenset({Verdict.HOLD, Verdict.BLOCK_PENDING, Verdict.UNKNOWN})

DEFAULT_TTL_SECONDS = 300.0


def new_trace_id() -> str:
    """INV-4. 건별 추적 식별자."""
    return "trc_" + secrets.token_hex(8)


def account_fingerprint(account: Account) -> str:
    """계좌 지문. 원본 계좌번호를 원장에 남기지 않기 위한 해시 (§7 저장 정책).

    공백·하이픈·대소문자는 표기 차이일 뿐이므로 정규화 후 해시한다.
    그렇지 않으면 `LT12 3250` 과 `lt1232 50` 이 다른 지문이 되어
    같은 계좌에 발급한 승인이 거부된다.
    """
    normalized = "".join(account.number.split()).replace("-", "").upper()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RemittanceApproval:
    """사람이 확인하고 발급한 승인 1건 (기술명세서 §6).

    frozen 인 이유: 발급 후 내용이 바뀌면 결박이 의미를 잃는다.
    소모(consumed) 상태만 원장이 별도로 관리한다.
    """

    approval_id: str
    case_id: str
    account_fingerprint: str
    approved_by: str
    verified_via: VerifyChannel
    issued_at: float
    trace_id: str
    ttl_seconds: float = DEFAULT_TTL_SECONDS

    def expires_at(self) -> float:
        return self.issued_at + self.ttl_seconds


@dataclass(frozen=True)
class AuditEvent:
    """append-only 감사 이벤트 (INV-4)."""

    trace_id: str
    case_id: str
    at: float
    kind: str      # issued | allowed | rejected
    detail: str


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str
    trace_id: str
    approval_id: str | None = None

    @property
    def blocked(self) -> bool:
        return not self.allowed


class ApprovalError(ValueError):
    """승인 발급 자체가 거부된 경우 (잘못된 채널 등)."""


@dataclass
class ApprovalLedger:
    """승인 원장. 이 객체가 승인의 유일한 진실 출처다 (INV-7).

    메모리 구현이다. 영속화는 은행 시스템 소관이며, 본 모듈이 강제하는 것은
    **판정 규칙**이지 저장 매체가 아니다.
    """

    _issued: dict[str, RemittanceApproval] = field(default_factory=dict)
    _consumed: set[str] = field(default_factory=set)
    _events: list[AuditEvent] = field(default_factory=list)

    # ── 발급 ──────────────────────────────────────────────────────────────
    def issue(
        self,
        *,
        case_id: str,
        account: Account,
        approved_by: str,
        verified_via: VerifyChannel | str,
        trace_id: str,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        now: float | None = None,
    ) -> RemittanceApproval:
        """사람이 확인을 마친 뒤 승인을 발급한다.

        `verified_via` 로 문자열도 받는다 — UI·API 경계에서 실제로 들어오는 형태가
        문자열이기 때문이다. 화이트리스트에 없으면 `ApprovalError` (T11).
        """
        now = time.time() if now is None else now

        if not case_id:
            raise ApprovalError("case_id 가 비어 있다 — 건에 결박할 수 없다")
        if not approved_by:
            raise ApprovalError("approved_by 가 비어 있다 — 누가 확인했는지 남지 않는다")

        try:
            channel = VerifyChannel(verified_via)
        except ValueError:
            raise ApprovalError(
                f"확인 채널 '{verified_via}' 는 허용되지 않는다. "
                f"허용: {[c.value for c in VerifyChannel]}. "
                "요청 메일 회신과 메일에 적힌 번호는 사기범이 받는다."
            ) from None

        approval = RemittanceApproval(
            approval_id="apv_" + secrets.token_hex(12),
            case_id=case_id,
            account_fingerprint=account_fingerprint(account),
            approved_by=approved_by,
            verified_via=channel,
            issued_at=now,
            trace_id=trace_id,
            ttl_seconds=ttl_seconds,
        )
        self._issued[approval.approval_id] = approval
        self._record(trace_id, case_id, now, "issued",
                     f"{approved_by} 가 {channel.value} 로 확인")
        return approval

    # ── 게이트 ────────────────────────────────────────────────────────────
    def gate(
        self,
        *,
        verdict: Verdict,
        case_id: str,
        account: Account,
        trace_id: str,
        approval_id: str | None = None,
        now: float | None = None,
    ) -> GateResult:
        """송금 실행 직전 관문 (INV-2).

        🔴 `approval_id` 는 **문자열**이다. 승인 객체를 받지 않는다 (INV-7).
        """
        now = time.time() if now is None else now

        if verdict not in _NEEDS_APPROVAL:
            return self._allow(trace_id, case_id, now,
                               f"{verdict.value} — 승인 불필요")

        if approval_id is None:
            return self._reject(trace_id, case_id, now,
                                f"{verdict.value} 는 승인 없이 통과할 수 없다")

        approval = self._issued.get(approval_id)
        if approval is None:
            # INV-7. 원장에 없는 id — 존재하지 않는 승인이다.
            return self._reject(trace_id, case_id, now,
                                "원장에 없는 승인 — 발급되지 않았다")

        if approval_id in self._consumed:
            return self._reject(trace_id, case_id, now,
                                "이미 사용된 승인 (재사용 차단)", approval_id)

        if approval.case_id != case_id:
            return self._reject(trace_id, case_id, now,
                                f"다른 건({approval.case_id})의 승인", approval_id)

        if approval.account_fingerprint != account_fingerprint(account):
            return self._reject(trace_id, case_id, now,
                                "승인된 계좌와 다른 계좌 (바꿔치기 차단)", approval_id)

        if now >= approval.expires_at():
            return self._reject(trace_id, case_id, now,
                                f"승인 만료 (TTL {approval.ttl_seconds:.0f}초)", approval_id)

        self._consumed.add(approval_id)
        return self._allow(trace_id, case_id, now,
                           f"{approval.approved_by} 가 {approval.verified_via.value} 로 확인",
                           approval_id)

    # ── 감사 ──────────────────────────────────────────────────────────────
    @property
    def events(self) -> tuple[AuditEvent, ...]:
        """append-only 감사 이벤트. 튜플로 반환해 외부에서 못 지우게 한다."""
        return tuple(self._events)

    def events_for(self, trace_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self._events if e.trace_id == trace_id)

    # ── 내부 ──────────────────────────────────────────────────────────────
    def _record(self, trace_id: str, case_id: str, at: float,
                kind: str, detail: str) -> None:
        self._events.append(AuditEvent(trace_id, case_id, at, kind, detail))

    def _allow(self, trace_id: str, case_id: str, at: float,
               reason: str, approval_id: str | None = None) -> GateResult:
        self._record(trace_id, case_id, at, "allowed", reason)
        return GateResult(True, reason, trace_id, approval_id)

    def _reject(self, trace_id: str, case_id: str, at: float,
                reason: str, approval_id: str | None = None) -> GateResult:
        self._record(trace_id, case_id, at, "rejected", reason)
        return GateResult(False, reason, trace_id, approval_id)
