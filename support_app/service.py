import asyncio
from uuid import uuid4

from support_app.models import SupportRequest, SupportResponse, TicketDraft
from support_app.routing import route_request
from support_app.security import Principal, validate_scope
from support_app.tools import ExecutionPolicy, ReadToolRunner, ReadTools, ToolUnavailable


class SupportService:
    def __init__(self, tools: ReadTools, policy: ExecutionPolicy) -> None:
        self.tools = tools
        self.policy = policy

    async def handle(self, request: SupportRequest, principal: Principal) -> SupportResponse:
        validate_scope(principal, request.product, request.version)
        decision = route_request(request)
        response = SupportResponse(
            request_id=str(uuid4()), route=decision.intent or "handoff",
            status="needs_human", reply="超出 M0 规则覆盖范围，请转人工确认。",
            trace=["scope_validated", "rule_routed"],
        )
        if decision.questions:
            response.status = "needs_info"
            response.questions = list(decision.questions)
            response.reply = "需要先补充信息；本次未调用工具。"
            response.trace.append("clarification_required")
            return response
        if decision.intent is None:
            response.trace.append("handoff")
            return response

        # The route cannot proceed without these fields; this also narrows their types.
        assert request.product is not None and request.version is not None
        if decision.intent == "create_ticket":
            response.status = "awaiting_confirmation"
            response.ticket_draft = TicketDraft(
                product=request.product, version=request.version,
                requester_id=principal.user_id,
                title=request.ticket_title or request.question[:100],
                description=request.question,
            )
            response.reply = "请核对工单草案参数。M0 未实现确认和创建接口，尚未创建工单。"
            response.trace.append("ticket_draft_only")
            return response

        runner = ReadToolRunner(self.policy)
        try:
            async with asyncio.timeout(self.policy.read_phase_timeout_seconds):
                response.evidence = await runner.call("search_documents", lambda:
                    self.tools.search_documents(
                        principal, request.product, request.version,
                        f"{request.question} {request.symptom or ''}",
                    ))
                response.trace.append("documents_read")
                if not response.evidence:
                    response.reply = "没有找到匹配产品、版本及主题的模拟资料，请转人工补充证据。"
                    response.trace.append("insufficient_evidence")
                    return response

                if decision.intent == "troubleshooting":
                    response.service_status = await runner.call("get_service_status", lambda:
                        self.tools.get_service_status(principal, request.product, request.version))
                    response.evidence.append(response.service_status.evidence)
                    response.trace.append("service_status_read")

                response.status = "answered"
                response.reply = "匹配版本的模拟资料摘要：\n" + "\n".join(
                    f"[{e.evidence_id}] {e.content}" for e in response.evidence
                )
                if response.service_status is not None:
                    response.reply += "\n以上仅为资料与固定状态快照，尚未确认用户问题的根因。"
                response.trace.append("baseline_answered")
        except (ToolUnavailable, TimeoutError):
            response.status = "tool_error"
            response.reply = "只读查询失败、超时或调用预算耗尽；无法完成答复，请稍后重试或转人工。"
            response.trace.append("read_failed")
        finally:
            response.tool_calls = runner.calls
        return response

