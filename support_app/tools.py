import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from support_app.models import Evidence, ServiceStatus, ToolCall
from support_app.security import Principal, validate_scope


class ToolUnavailable(Exception):
    """Expected dependency failure; do not put upstream secrets in responses."""


class ReadTools(Protocol):
    async def search_documents(
        self, principal: Principal, product: str, version: str, query: str,
    ) -> list[Evidence]: ...

    async def get_service_status(
        self, principal: Principal, product: str, version: str,
    ) -> ServiceStatus: ...


class MockReadTools:
    """Local fixture adapter. Async shape allows a later I/O adapter replacement."""

    def __init__(self) -> None:
        data = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "product.json",
        ).read_text(encoding="utf-8"))
        self.documents = [
            (record["keywords"], record.get("symptom_keywords", []),
             Evidence.model_validate(record["evidence"]))
            for record in data["documents"]
        ]
        self.statuses = [ServiceStatus.model_validate(item) for item in data["statuses"]]

    async def search_documents(
        self, principal: Principal, product: str, version: str, query: str,
    ) -> list[Evidence]:
        validate_scope(principal, product, version)
        query = query.casefold()
        return [e.model_copy(deep=True) for words, symptoms, e in self.documents
                if e.product == product and e.version == version
                and any(word in query for word in words)
                and (not symptoms or any(word in query for word in symptoms))]

    async def get_service_status(
        self, principal: Principal, product: str, version: str,
    ) -> ServiceStatus:
        validate_scope(principal, product, version)
        for status in self.statuses:
            if status.evidence.product == product and status.evidence.version == version:
                return status.model_copy(deep=True)
        raise ToolUnavailable("fixture status missing")


@dataclass(frozen=True)
class ExecutionPolicy:
    tool_timeout_seconds: float = 0.5
    read_phase_timeout_seconds: float = 2.0
    max_tool_calls: int = 2

    def __post_init__(self) -> None:
        if self.tool_timeout_seconds <= 0 or self.read_phase_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive")


T = TypeVar("T")
ToolName = Literal["search_documents", "get_service_status"]


class ReadToolRunner:
    """Request-local budget; one attempt per read, no implicit retries or writes."""

    def __init__(self, policy: ExecutionPolicy) -> None:
        self.policy = policy
        self.calls: list[ToolCall] = []

    async def call(self, name: ToolName, operation: Callable[[], Awaitable[T]]) -> T:
        if len(self.calls) >= self.policy.max_tool_calls:
            # Record the blocked attempt, which never invokes the adapter.
            self.calls.append(ToolCall(name=name, outcome="budget_exceeded"))
            raise ToolUnavailable("call budget exhausted")
        call = ToolCall(name=name, outcome="ok")
        self.calls.append(call)
        try:
            async with asyncio.timeout(self.policy.tool_timeout_seconds):
                return await operation()
        except TimeoutError as exc:
            call.outcome = "timeout"
            raise ToolUnavailable("read timed out") from exc
        except ToolUnavailable:
            call.outcome = "unavailable"
            raise
        except asyncio.CancelledError:
            # Parent deadline or external cancellation: do not swallow cancellation.
            call.outcome = "cancelled"
            raise

