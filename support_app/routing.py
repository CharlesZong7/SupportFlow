from dataclasses import dataclass

from support_app.models import Intent, SupportRequest


@dataclass(frozen=True)
class RouteDecision:
    intent: Intent | None
    questions: tuple[str, ...] = ()


def route_request(request: SupportRequest) -> RouteDecision:
    """Small deterministic baseline, not an Agent or general NLU classifier."""
    intent = request.intent
    if intent is None:
        question = request.question.casefold()
        if "工单" in question or "ticket" in question:
            intent = "create_ticket"
        elif request.symptom or any(word in question for word in (
            "超时", "报错", "失败", "故障", "timeout", "error",
        )):
            intent = "troubleshooting"
        elif any(word in question for word in ("导出", "export", "csv")):
            intent = "consultation"

    questions = []
    if request.product is None:
        questions.append("请提供产品标识（演示产品为 nimbusdesk）。")
    if request.version is None:
        questions.append("请提供准确版本（演示版本为 1.0 或 1.1）。")
    if intent == "troubleshooting" and request.symptom is None:
        questions.append("请补充具体现象、错误信息及发生条件，填写 symptom。")
    return RouteDecision(intent, tuple(questions))

