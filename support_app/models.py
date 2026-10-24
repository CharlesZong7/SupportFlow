from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Intent = Literal["consultation", "troubleshooting", "create_ticket"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupportRequest(Contract):
    question: Annotated[Text, Field(min_length=2, max_length=2000)]
    product: Annotated[Text, Field(max_length=64)] | None = None
    version: Annotated[Text, Field(max_length=32)] | None = None
    intent: Intent | None = None
    symptom: Annotated[Text, Field(max_length=1000)] | None = None
    ticket_title: Annotated[Text, Field(max_length=100)] | None = None


class Evidence(Contract):
    evidence_id: str
    product: str
    version: str
    kind: Literal["manual", "release_notes", "service_status"]
    source: str
    content: str
    simulated: Literal[True] = True


class ServiceStatus(Contract):
    state: Literal["operational", "degraded"]
    # Fixed fixture timestamp, never presented as a live observation.
    recorded_at: str
    evidence: Evidence


class TicketDraft(Contract):
    action: Literal["create_ticket"] = "create_ticket"
    product: str
    version: str
    requester_id: str
    title: str
    description: str
    confirmation_required: Literal[True] = True
    execution_available: Literal[False] = False


class ToolCall(Contract):
    name: Literal["search_documents", "get_service_status"]
    outcome: Literal["ok", "timeout", "unavailable", "budget_exceeded", "cancelled"]


class SupportResponse(Contract):
    request_id: str
    mode: Literal["mock"] = "mock"
    status: Literal[
        "answered", "needs_info", "needs_human", "awaiting_confirmation", "tool_error"
    ]
    route: Intent | Literal["handoff"]
    reply: str
    questions: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    service_status: ServiceStatus | None = None
    ticket_draft: TicketDraft | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "M0 规则业务基线；所有资料与状态均为模拟数据，未调用模型。",
        "请求内执行，无任务持久化、后台恢复或工单写入能力。",
    ])

