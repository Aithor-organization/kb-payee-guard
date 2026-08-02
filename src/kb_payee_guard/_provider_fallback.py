"""AITHOR-Agent-Framework 부재 시 쓰는 최소 OpenAI provider (stdlib only).

## 왜 필요한가 — 2026-08-02 실측

제출 zip 을 풀어 심사자 환경을 재현했더니 **테스트 13건이 깨졌다.**
원인은 프레임워크 import 경로였다:

    _FRAMEWORK_SRC = Path(__file__).resolve().parents[3] / "AITHOR-Agent-Framework" / "src"

내 작업 환경에서는 `parents[3]` 이 `~/workspace` 라 sibling repo 를 정확히 가리킨다.
그러나 zip 을 임의 위치에 풀면 그 상대 경로가 성립하지 않는다. 그리고 더 근본적으로,
**AITHOR-Agent-Framework 는 private repo 라 심사자가 클론할 수 없다.**

제출물은 **단독으로 돌아야 한다.** 그래서 프레임워크가 있으면 그것을 쓰고,
없으면 같은 인터페이스의 최소 구현으로 떨어진다.

## 인터페이스 계약

프레임워크의 `OpenAIProvider` 와 **동일한 생성자 인자·동일한 반환 형태**를 유지한다:

    OpenAIProvider(model=, temperature=, json_schema=, schema_name=, transport=, api_key=)
    .complete(messages, tools) -> LLMResponse(kind, content)

`json_schema` 를 주면 OpenAI 의 `response_format={"type":"json_schema", …, "strict": true}`
로 감싼다 — 스키마를 벗어난 출력이 API 레벨에서 차단되는 성질을 그대로 보존한다.
이것이 INV-6(LLM 에 판정 권한을 주지 않는다)의 기계적 근거이므로 타협할 수 없다.

`transport` 를 주입하면 네트워크 없이 돈다 — 테스트가 API 키 없이 완주하는 이유다.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

DEFAULT_TIMEOUT = 60.0          # FP#1 — API 타임아웃 누락 금지


@dataclass
class LLMResponse:
    """프레임워크 `agent_loop.LLMResponse` 와 같은 모양 (필요한 필드만)."""

    kind: str = "final"
    content: str = ""
    tool_calls: tuple = ()
    usage: dict[str, int] | None = None


def _default_transport(url: str, headers: dict[str, str], body: bytes,
                       timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as f:
            return json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"OpenAI HTTP {e.code}: {detail}") from e


@dataclass
class OpenAIProvider:
    """프레임워크 미탑재 환경용 대체 구현. 인터페이스는 동일하다."""

    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.0
    timeout: float = DEFAULT_TIMEOUT
    transport: Callable[..., dict] | None = None
    json_schema: dict[str, Any] | None = None
    schema_name: str = "structured_output"
    response_format: dict[str, Any] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        if self.json_schema is not None:
            self.response_format = {
                "type": "json_schema",
                "json_schema": {"name": self.schema_name,
                                "schema": dict(self.json_schema),
                                "strict": True},
            }

    def complete(self, messages: list[dict[str, Any]],
                 tools: list[dict[str, Any]]) -> LLMResponse:   # noqa: ARG002
        if not self.api_key and self.transport is None:
            raise RuntimeError(
                "OPENAI_API_KEY 가 없습니다. .env 에 넣거나 환경변수로 주세요 — "
                "테스트는 transport 주입으로 키 없이 돕니다."
            )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.response_format is not None:
            payload["response_format"] = self.response_format

        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        send = self.transport or _default_transport

        try:
            data = send(url, headers, body, self.timeout)
        except RuntimeError as exc:
            # 추론 모델은 기본값 아닌 temperature 를 400 으로 거부한다 — 1회 재시도
            if "temperature" in payload and "temperature" in str(exc):
                payload.pop("temperature", None)
                data = send(url, headers, json.dumps(payload).encode("utf-8"), self.timeout)
            else:
                raise

        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"예상치 못한 응답 형태: {str(data)[:200]}") from exc
        return LLMResponse(kind="final", content=msg.get("content") or "",
                           usage=data.get("usage"))
