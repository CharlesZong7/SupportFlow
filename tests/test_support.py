import asyncio
import unittest

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from support_app.main import create_app
from support_app.models import SupportRequest
from support_app.security import DEMO_IDENTITIES
from support_app.service import SupportService
from support_app.tools import ExecutionPolicy, MockReadTools, ToolUnavailable


BASE = {"product": "nimbusdesk", "version": "1.1", "question": "导出 CSV 最多多少行？"}
TROUBLE = {**BASE, "question": "导出超时怎么办？", "symptom": "报表导出 30 秒后超时"}


class BrokenStatus(MockReadTools):
    async def get_service_status(self, *args, **kwargs):
        raise ToolUnavailable("upstream private details must not reach the user")


class SlowStatus(MockReadTools):
    def __init__(self):
        super().__init__()
        self.started = asyncio.Event()
        self.cleaned_up = False

    async def get_service_status(self, *args, **kwargs):
        self.started.set()
        try:
            await asyncio.sleep(10)
        finally:
            self.cleaned_up = True


class SupportTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, payload, token="dev-alice", tools=None, policy=None):
        app = create_app(tools, policy)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            return await client.post("/api/support", json=payload, headers=headers)

    async def test_consultation_uses_one_read(self):
        response = await self.request(BASE)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["mode"], body["status"], body["route"]),
                         ("mock", "answered", "consultation"))
        self.assertIn("5000", body["reply"])
        self.assertEqual(body["tool_calls"], [{"name": "search_documents", "outcome": "ok"}])
        self.assertEqual(body["evidence"][0]["evidence_id"], "MANUAL-1.1-EXPORT")

    async def test_troubleshooting_uses_docs_then_status(self):
        body = (await self.request(TROUBLE)).json()
        self.assertEqual(body["status"], "answered")
        self.assertEqual(body["service_status"]["state"], "degraded")
        self.assertEqual([call["name"] for call in body["tool_calls"]],
                         ["search_documents", "get_service_status"])
        self.assertEqual(len(body["evidence"]), 3)
        self.assertIn("尚未确认", body["reply"])

    async def test_version_is_filtered_before_returning_evidence(self):
        body = (await self.request({**BASE, "version": "1.0"})).json()
        self.assertIn("1000", body["reply"])
        self.assertNotIn("5000", body["reply"])
        self.assertTrue(all(item["version"] == "1.0" for item in body["evidence"]))

    async def test_missing_version_stops_before_tools(self):
        payload = {**BASE}
        del payload["version"]
        body = (await self.request(payload)).json()
        self.assertEqual(body["status"], "needs_info")
        self.assertTrue(body["questions"])
        self.assertEqual(body["tool_calls"], [])

    async def test_missing_product_stops_before_tools(self):
        body = (await self.request({"question": "导出 CSV 怎么使用？"})).json()
        self.assertEqual(body["status"], "needs_info")
        self.assertEqual(len(body["questions"]), 2)
        self.assertEqual(body["evidence"], [])

    async def test_missing_symptom_asks_explicitly(self):
        body = (await self.request({**BASE, "question": "导出超时怎么办？"})).json()
        self.assertEqual(body["status"], "needs_info")
        self.assertIn("symptom", body["questions"][0])
        self.assertEqual(body["tool_calls"], [])

    async def test_unknown_product_and_version_rejected(self):
        for update in ({"product": "other"}, {"version": "9.9"}):
            with self.subTest(update=update):
                self.assertEqual((await self.request({**BASE, **update})).status_code, 400)

    async def test_identity_is_required(self):
        for token in (None, "not-a-demo-token"):
            with self.subTest(token=token):
                self.assertEqual((await self.request(BASE, token=token)).status_code, 401)

    async def test_product_version_permission_is_checked_on_server(self):
        self.assertEqual((await self.request(BASE, token="dev-bob")).status_code, 403)
        self.assertEqual((await self.request({**BASE, "version": "1.0"}, token="dev-bob")).status_code, 200)

    async def test_tool_interface_also_enforces_permission(self):
        tools = MockReadTools()
        bob = DEMO_IDENTITIES["dev-bob"]
        for operation in (tools.search_documents(bob, "nimbusdesk", "1.1", "导出"),
                          tools.get_service_status(bob, "nimbusdesk", "1.1")):
            with self.assertRaises(HTTPException) as raised:
                await operation
            self.assertEqual(raised.exception.status_code, 403)

    async def test_ticket_is_only_an_exact_draft(self):
        payload = {**BASE, "question": "请创建工单：导出报错", "ticket_title": "导出报错"}
        body = (await self.request(payload)).json()
        self.assertEqual(body["status"], "awaiting_confirmation")
        self.assertEqual(body["tool_calls"], [])
        self.assertEqual(body["ticket_draft"], {
            "action": "create_ticket", "product": "nimbusdesk", "version": "1.1",
            "requester_id": "demo-alice", "title": "导出报错",
            "description": payload["question"], "confirmation_required": True,
            "execution_available": False,
        })

    async def test_extra_identity_or_confirmation_cannot_be_injected(self):
        for update in ({"user_id": "other-user"}, {"confirmed": True}, {"mode": "real"}):
            with self.subTest(update=update):
                self.assertEqual((await self.request({**BASE, **update})).status_code, 422)

    async def test_blank_question_is_rejected(self):
        self.assertEqual((await self.request({**BASE, "question": "  "})).status_code, 422)

    async def test_explicit_intent_does_not_remove_required_diagnostic_fields(self):
        body = (await self.request({**BASE, "intent": "troubleshooting"})).json()
        self.assertEqual(body["status"], "needs_info")
        self.assertEqual(body["tool_calls"], [])

    async def test_unrecognized_intent_goes_to_human(self):
        body = (await self.request({**BASE, "question": "请帮我计算采购预算"})).json()
        self.assertEqual((body["status"], body["route"]), ("needs_human", "handoff"))
        self.assertEqual(body["tool_calls"], [])

    async def test_no_evidence_does_not_invent_answer_or_status(self):
        payload = {**TROUBLE, "question": "登录超时", "symptom": "登录十秒后超时"}
        body = (await self.request(payload)).json()
        self.assertEqual(body["status"], "needs_human")
        self.assertEqual(body["evidence"], [])
        self.assertIsNone(body["service_status"])
        self.assertEqual(len(body["tool_calls"]), 1)

    async def test_status_failure_preserves_only_actual_documents(self):
        body = (await self.request(TROUBLE, tools=BrokenStatus())).json()
        self.assertEqual(body["status"], "tool_error")
        self.assertIsNone(body["service_status"])
        self.assertTrue(body["evidence"])
        self.assertNotIn("service_status", [item["kind"] for item in body["evidence"]])
        self.assertEqual(body["tool_calls"][-1]["outcome"], "unavailable")
        self.assertNotIn("private details", str(body))

    async def test_read_timeout_cancels_dependency_and_does_not_retry(self):
        tools = SlowStatus()
        body = (await self.request(TROUBLE, tools=tools, policy=ExecutionPolicy(
            tool_timeout_seconds=0.02,
        ))).json()
        self.assertEqual(body["status"], "tool_error")
        self.assertEqual(body["tool_calls"][-1]["outcome"], "timeout")
        self.assertEqual(len(body["tool_calls"]), 2)
        self.assertTrue(tools.cleaned_up)

    async def test_read_phase_deadline_cancels_inflight_read(self):
        tools = SlowStatus()
        body = (await self.request(TROUBLE, tools=tools, policy=ExecutionPolicy(
            tool_timeout_seconds=1, read_phase_timeout_seconds=0.02,
        ))).json()
        self.assertEqual(body["status"], "tool_error")
        self.assertEqual(body["tool_calls"][-1]["outcome"], "cancelled")
        self.assertTrue(tools.cleaned_up)

    async def test_tool_budget_blocks_further_adapter_calls(self):
        tools = SlowStatus()
        body = (await self.request(TROUBLE, tools=tools, policy=ExecutionPolicy(
            max_tool_calls=1,
        ))).json()
        self.assertEqual(body["status"], "tool_error")
        self.assertEqual(body["tool_calls"][-1]["outcome"], "budget_exceeded")
        self.assertFalse(tools.started.is_set())

    async def test_external_cancellation_propagates_and_cleans_up(self):
        tools = SlowStatus()
        service = SupportService(tools, ExecutionPolicy())
        task = asyncio.create_task(service.handle(
            SupportRequest(**TROUBLE), DEMO_IDENTITIES["dev-alice"],
        ))
        await asyncio.wait_for(tools.started.wait(), timeout=1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(tools.cleaned_up)

    async def test_simultaneous_requests_have_independent_budgets(self):
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = await asyncio.gather(*[
                client.post("/api/support", json=TROUBLE, headers={
                    "Authorization": "Bearer dev-alice",
                }) for _ in range(3)
            ])
        bodies = [r.json() for r in responses]
        self.assertEqual(len({b["request_id"] for b in bodies}), 3)
        self.assertTrue(all(b["status"] == "answered" and len(b["tool_calls"]) == 2 for b in bodies))


if __name__ == "__main__":
    unittest.main()
