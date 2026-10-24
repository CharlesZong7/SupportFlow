# 源码课程：企业技术支持业务基线

源码轮次：本地 M0-001，尚无 Git 提交。本轮从空目录新建代码；后续修改需同步更新本课程的调用链。前置知识：Python 函数、类型标注、Pydantic 模型、HTTP 请求和 `await` 的基本含义。

覆盖范围：一次请求的校验、规则路由、模拟只读工具、草案和失败返回。尚未实现模型角色、LangGraph、数据库、队列、恢复、MCP 或部署，不能为它们给出当前调用链。

## 01 · 一个问题如何走到有证据的结构化结果

状态：**已展开**。读完应能解释：哪些请求需要工具，哪些请求提前停止，失败时已有证据和业务操作分别处于什么状态。

### 场景与主链

提交 `nimbusdesk / 1.1 / 导出超时怎么办？ / symptom=报表导出 30 秒后超时`：

`首页 fetch 或 HTTP 客户端 → POST /api/support → 请求结构与身份依赖 → SupportService.handle → validate_scope → route_request → search_documents → get_service_status → SupportResponse`

此请求经历两个顺序 `await`，并非并行。它没有模型决策、复核 Agent 或后台任务，输出只汇总实际返回的模拟资料与状态。

### 编号阅读顺序

1. `support_app/main.py::create_app / submit_support`：框架将请求体解析为 `SupportRequest`，通过依赖获得 `Principal`，把两者交给 `SupportService.handle`。端点保持薄，只负责 HTTP 到业务的衔接。
2. `support_app/models.py::SupportRequest / SupportResponse`：确认输入允许哪些字段、哪些字段可缺省，以及结果状态如何表达。结构合法不意味着业务信息已经充分；缺版本的请求结构合法，会进入补问分支。
3. `support_app/security.py::get_principal / validate_scope`：公开演示凭据决定服务端身份，客户端不能在请求体指定身份。产品存在性、版本存在性、授权是确定性检查，不能交给后续模型决定。失败抛 HTTPException，不进入工具链。
4. `support_app/routing.py::route_request`：优先使用显式意图，否则以有限关键词确定意图。产品、版本、必要诊断现象缺失时收集补问，不做模糊猜测。输出 `RouteDecision`，它是规则结果，不是 Agent 推理。
5. `support_app/service.py::SupportService.handle`：看清补问、未知意图、工单草案三个提前返回点，再看只读阶段。它负责业务顺序，决定何时停止以及如何把证据放进响应。
6. `support_app/tools.py::ReadToolRunner.call / MockReadTools`：前者管理每请求预算和超时，后者只读 fixture 并再次校验权限。输入是明确的产品、版本、查询和服务端身份；输出是结构化 Evidence 或 ServiceStatus。
7. `support_app/models.py::Evidence / ServiceStatus / TicketDraft`：沿返回路径核对证据的出处、模拟标记及状态快照时间。不要把草案中的 `requester_id` 与客户端可写的身份混淆，也不要把 `awaiting_confirmation` 理解为已经存好了可恢复审批单。

选读验证：`tests/test_support.py::test_troubleshooting_uses_docs_then_status`、`test_no_evidence_does_not_invent_answer_or_status`、`test_ticket_is_only_an_exact_draft`；`scripts/smoke_http.py::main` 则通过真实本地端口复走请求链。

### 沿流程理解取舍

**结构与业务充分性分开。** `SupportRequest` 拒绝未知字段并限制空白及长度；允许缺少 product/version，是为了让业务返回有针对性的补问。服务不是收到合法 JSON 就必须调用工具。

**权限先于业务读取。** `validate_scope` 在 service 入口检查，工具自身也检查。前者让请求尽早失败，后者给未来其他入口留下可复用的服务端边界。当前只保护产品版本，没有尚不存在的历史工单归属策略。

**分诊只决定路径。** 故障排查缺 `symptom` 就停止，即使 question 已经出现“超时”，也不假定错误上下文足够。这里是刻意采用的 M0 规则；未来可由模型提取候选字段，但提取结果仍需确定性校验。

**工具接口与实现分开。** `ReadTools` 定义方法签名，不知道文件、网络或 MCP；`MockReadTools` 读取明确标记的 fixture。service 通过构造函数注入工具，测试因此能替换失败或慢工具，不需要在公共 API 暴露故障开关。

**证据先于摘要。** 查询按产品、准确版本、主题匹配。没有资料直接 `needs_human`；不会拿全局状态冒充问题证据。故障排查成功时把实际状态结果附到资料后，再生成包含 ID 的原文摘要，不产生新的根因断言。

**预算属于单次请求。** `ReadToolRunner` 在 `handle` 内新建，三个并发请求不会共用调用次数。成功的只读操作最多两次；预算拦截会记录一个未执行的尝试，所以审计列表长度不必等于实际执行次数。

### 在实际分支上看停止条件

| 触发 | 代码落点 | 返回/已发生的事情 |
| --- | --- | --- |
| 缺版本或现象 | `decision.questions` 分支 | `needs_info`，没有读取工具；补齐后重新提交完整请求 |
| 未知意图 | `decision.intent is None` | `needs_human`，没有读取工具 |
| 工单请求 | `create_ticket` 分支 | 仅草案，身份取自 Principal，无写工具，无持久化审批 |
| 无匹配资料 | `if not response.evidence` | `needs_human`，只执行了资料查询，不读状态 |
| 单次只读超时 | runner 的 `asyncio.timeout` | 将该调用标记 `timeout`，转 ToolUnavailable，返回 `tool_error` |
| 只读阶段超时 | service 的 `asyncio.timeout` | 取消正在等待的工具，runner 记录 `cancelled`；service 返回 `tool_error` |
| 外部取消 service 协程 | runner 的 CancelledError 分支 | 标记并继续抛出，没有正常业务响应；等待中的模拟工具 finally 被执行 |

工具失败时，如果资料已经返回，它们仍在响应里；失败的状态查询不产生状态结果。代码没有重试，也没有恢复点或结果查询接口。`asyncio.timeout` 依赖协程让出执行，不能强行终止一段阻塞 CPU 或同步 I/O。

### 用一次输入重新串联

对于上述 1.1 导出超时请求，服务端确认 Alice 可以访问该版本，规则识别为排查，字段充分后依次读取 `MANUAL-1.1-EXPORT`、`RELEASE-1.1-EXPORT` 和 `STATUS-1.1-EXPORT`。只有工具成功返回后，响应才包含对应状态；最终仍说明根因未确认。若第二次调用失败，路径在 `read_failed` 停止，不编造状态；若改成工单请求，则从草案分支提前返回，整条读取路径不会执行。

自行复述任务：选一个正常输入和一个失败变体，按“谁给出身份 → 谁决定路径 → 工具实际执行了哪些 → 最终有哪些已完成结果”讲一遍。相关题目在 `practice.md`，无需背字段拼写。

### 后续课程边界

M1 的模型适配器将负责输出候选分诊结构，M2 的 LangGraph 将组织四角色协作，M3 才引入任务持久化和可靠写入。这些是设计计划，尚无可阅读的实现路径；当前不建立虚构课程调用链。

若某文件或原理看不懂，请继续追问 AI；本轮按实际流程解释设计，不逐行复述语法。用户笔记后续追加，保留原文。

