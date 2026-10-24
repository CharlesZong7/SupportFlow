# SupportFlow · 企业技术支持与工单协作系统

当前为 **M0：可运行的规则业务基线**。使用虚构产品 NimbusDesk 的模拟资料验证流程。没有模型调用、真实 Agent 协作、数据库、Worker 或工单写入；项目名称代表最终目标。

先了解“为谁做、什么时候用、技术栈和每阶段做什么”，请阅读 [项目定位与开发计划](docs/项目定位与开发计划.md)。文档区分当前实现与完成体目标。

将本地项目发布到个人 GitHub 仓库，见 [GitHub 开源发布步骤](docs/GitHub开源发布步骤.md)。

## 现在能运行什么

`提交问题 → 结构校验与演示身份校验 → 产品/版本授权 → 规则分诊 → 按需查询模拟资料与状态 → 结构化结果`

- 产品咨询：匹配版本与主题的资料摘要，附证据 ID、来源、内容及模拟标记。
- 故障排查：先查询资料，再读取固定服务状态快照，不确认用户环境的根因。
- 信息不足：补问后停止；用户补齐字段，重新提交完整请求。
- 资料不足或未知意图：返回 `needs_human`，没有真实转人工系统。
- 工单请求：准确展示草案参数，返回 `awaiting_confirmation`；`execution_available=false`。本轮没有确认或创建接口。
- 两个公开演示身份，服务端校验可访问的产品版本。没有用户历史工单等私有资源，尚未验证此类资源的归属隔离。

## 在当前工作区运行

已创建 `.venv`，通过 `--system-site-packages` 复用预装依赖，无需激活 PowerShell 环境：

```powershell
Set-Location 'D:\multi agent'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn support_app.main:app --host 127.0.0.1 --port 8000
```

打开 [本地交互入口](http://127.0.0.1:8000/)：原生表单、无外部脚本或 CDN，可离线向本地 API 提交请求。界面不保存问题和凭据。也可打开 [Swagger](http://127.0.0.1:8000/docs)，其 UI 资源需要联网；点击 Authorize 输入 `dev-alice`。

公开演示凭据仅用于本机学习：`dev-alice` 可访问 `nimbusdesk` 的 `1.0`、`1.1`；`dev-bob` 仅可访问 `1.0`。这不是生产身份认证，不应部署到公网。

新机器或全新隔离环境安装方式（需要可访问软件包源；本轮未验证全新安装）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 固定本轮已验证的直接依赖：FastAPI 0.142.1、Pydantic 2.13.4、Uvicorn 0.54.0、HTTPX 0.28.1。Python 实测为 3.12.5。传递依赖尚未完整锁定。LangGraph 1.2.9 已安装且可导入，但本轮没有使用或声明为运行依赖。

## API 示例

```powershell
$demoHeaders = @{ Authorization = 'Bearer dev-alice' }
$supportBody = @{
  product = 'nimbusdesk'
  version = '1.1'
  question = '导出超时怎么办？'
  symptom = '报表导出 30 秒后超时'
} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/support' -Method Post -Headers $demoHeaders -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($supportBody))
```

预期 `mode=mock`、`status=answered`、`route=troubleshooting`，返回手册、版本说明与状态三条证据；`service_status.state=degraded` 仅是固定模拟值。时间来自 fixture 的 `recorded_at`，不是实时状态。`mock://` 表示本地数据来源标识，不是可访问的外部链接。

在交互入口可依次尝试：

| 问题 / 调整 | 结果 |
| --- | --- |
| 导出 CSV 最多多少行？ | 咨询；1.0 为 1000 行，1.1 为 5000 行，仅为模拟产品规则 |
| 导出超时怎么办？并填写现象 | 资料与状态摘要，工具顺序调用 |
| 不填写版本，或排查时不填写现象 | `needs_info`，零工具调用 |
| 登录超时，并填写登录现象 | `needs_human`，不套用导出资料 |
| 请创建工单：导出报错 | 仅返回工单草案，未创建工单 |
| `dev-bob` 查询 1.1 | HTTP 403 |

`intent` 可显式填写 `consultation`、`troubleshooting`、`create_ticket`；不填时使用有限关键词规则。产品、版本、诊断现象由结构化字段提供，尚未实现模型提取。显式意图不会绕过权限或必填诊断字段检查。

HTTP 200 表示业务流程正常返回，仍需检查 `status`；`needs_info`、`needs_human`、`tool_error` 都不代表问题已解决。401 为身份失败，403 为权限失败，400 为未知产品/版本，422 为结构校验失败。`request_id` 只用于区分本次响应，不是可恢复或可查询的任务 ID。

## 验证

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\smoke_http.py
```

第一条执行 22 项 ASGI/API 及业务测试；第二条临时启动真实 Uvicorn 本地端口，验证首页、OpenAPI、健康检查和 7 个 HTTP 案例，结束时关闭该临时服务，将结果保存到 `docs/validation/m0-http.json`。这些都是本地 mock 验证，不是实际模型效果或部署、压力测试。

## 当前执行边界

- `ReadTools` 是只读接口，当前适配器只读本地 fixture；没有写工具。后续模型及 MCP 适配器应复用服务端校验边界，而不是信任提示词。
- 每次只读工具调用上限 0.5 秒，整个只读查询阶段 2 秒，最多执行两次工具调用，每次只有一次尝试、零重试。预算拒绝会额外记录一个未执行的 `budget_exceeded` 审计项。
- 整体超时只包围只读阶段，不包括 HTTP 接收、鉴权及路由。`asyncio.timeout` 是协作式取消，无法强行中断同步阻塞；当前 fixture 的 `async def` 主要是保留接口，不能据此声称实现了并行 I/O。
- 发生工具失败或超时，保留实际已查到的资料；不补造状态。取消向下传播，不吞掉 `CancelledError`。
- 已验证主动取消 service 协程会清理等待中的模拟工具。浏览器断线不保证自动取消服务端请求；此行为尚未验证。页面的 5 秒超时只是停止客户端等待。
- 刷新、断线、进程重启后没有任务/对话状态可恢复。本轮没有业务写入，所以不会遗留已创建但不可查询的工单。未来写操作必须另做确认、持久化和幂等设计。
- 应用始终明确处于 mock 模式，不读取或使用模型密钥。尚未验证外部模型、真实服务状态或真实工单服务。

## 学习与阶段计划

| 阶段 | 验收与边界 |
| --- | --- |
| M0，本轮完成 | 本地 API、结构化契约、规则分诊、模拟只读工具、失败分支与草案 |
| M1，未开始 | 模型适配器、结构化角色契约、格式错误/不可用/信息不足验证；真实调用单独记录 |
| M2，未开始 | LangGraph 四角色按需协作、独立读取并发、证据复核、停止条件与单 Agent 对照 |
| M3，未开始 | PostgreSQL、Redis + ARQ，逐轮补齐可靠执行、重发、恢复、幂等与工单确认执行 |
| M4，未开始 | MCP 服务、Compose、SSE、结构化日志、可选观测与分层评测 |

源码阅读和本轮解释见 [tutorial.md](tutorial.md)，理解题见 [practice.md](practice.md)。每轮更新 [学习记录](docs/学习记录.md) 与 [实现与验证清单](docs/实现与验证清单.md)。`M0-001` 为首轮开发记录编号，后续代码版本以实际 Git 历史为准。

## 开发与参考说明

SupportFlow 是 AI 辅助开发的实践项目，NimbusDesk 是用于验证流程的虚构产品。业务资料均为模拟材料，未接入企业真实数据，当前没有已确认的生产上线或业务效果。

已阅读 Yuxi 的选定实现作为后续设计参考，来源、固定提交和差异见 [参考阅读](docs/参考阅读-Yuxi.md)；尚未移植其代码。本项目当前尚未添加 `LICENSE`，发布前后需按 [开源发布步骤](docs/GitHub开源发布步骤.md) 明确选定许可。

