"""전송 계층 재시도 — 일시적 실패에 죽지 않는가.

🔴 회귀 방지 대상: 2026-08-02 에 holdout 232건 평가가 129건째 `TimeoutError` 로
   중단돼 10분치 작업이 통째로 사라졌다. 재시도가 없었던 것이 원인이다.
   네트워크는 실제로 쓰지 않는다 — urlopen 을 가짜로 바꿔 호출 횟수만 센다.
"""
from __future__ import annotations

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kb_payee_guard import _provider_fallback as P  # noqa: E402


class _FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _ok():
    return _FakeResp(b'{"choices":[{"message":{"content":"{}"}}]}')


def _http(code: int):
    return urllib.error.HTTPError("https://example.invalid/v1", code, "e", {}, io.BytesIO(b"boom"))


class TransportRetry(unittest.TestCase):
    def _run(self, side_effect):
        with mock.patch.object(P.urllib.request, "urlopen", side_effect=side_effect) as m, \
             mock.patch.object(P.time, "sleep") as sl:      # 대기는 건너뛴다
            try:
                out = P._default_transport("https://example.invalid/v1", {}, b"{}", 1.0)
            except Exception as e:                          # noqa: BLE001
                out = e
        return out, m.call_count, sl.call_count

    def test_transient_timeout_is_retried_and_succeeds(self):
        """첫 두 번 타임아웃 → 세 번째 성공. 이게 없어서 실제 실행이 죽었다."""
        out, calls, sleeps = self._run([TimeoutError("t"), TimeoutError("t"), _ok()])
        self.assertIsInstance(out, dict)
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, 2)

    def test_gives_up_after_max_retries(self):
        """무한 재시도는 하지 않는다 — 3회 후 마지막 원인을 올린다."""
        out, calls, _ = self._run([TimeoutError("t")] * 5)
        self.assertIsInstance(out, RuntimeError)
        self.assertIn("TimeoutError", str(out))
        self.assertEqual(calls, P.MAX_RETRIES)

    def test_client_error_is_not_retried(self):
        """401/400 은 재시도해도 같은 답 — 즉시 올린다 (조용히 3배 느려지면 안 된다)."""
        out, calls, sleeps = self._run([_http(401)] * 3)
        self.assertIsInstance(out, RuntimeError)
        self.assertIn("401", str(out))
        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, 0)

    def test_server_error_is_retried(self):
        """5xx·429 는 서버측 일시 오류라 재시도 대상."""
        out, calls, _ = self._run([_http(503), _ok()])
        self.assertIsInstance(out, dict)
        self.assertEqual(calls, 2)

    def test_rate_limit_is_retried(self):
        out, calls, _ = self._run([_http(429), _ok()])
        self.assertIsInstance(out, dict)
        self.assertEqual(calls, 2)

    def test_url_error_is_retried(self):
        """DNS·연결 실패도 일시적일 수 있다."""
        out, calls, _ = self._run([urllib.error.URLError("dns"), _ok()])
        self.assertIsInstance(out, dict)
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
