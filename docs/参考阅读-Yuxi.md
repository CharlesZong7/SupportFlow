# Yuxi 参考阅读摘要

来源核对日期：2026-10-24。本文件补齐现有学习记录所引用的阅读摘要；依据本次对话此前完成的远程源码阅读整理。本轮编写项目总览时未重新读取远程仓库。

## 固定版本与许可

- 仓库：<https://github.com/xerrors/Yuxi>
- 当时实际默认分支：`main`。
- 固定提交：`928141ceb2799cee18bcdbc060618ab9151ba48b`。
- [项目 LICENSE](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/LICENSE)：MIT；部署中第三方组件的许可未逐项审计。
- 当时 README 的启动示例与后端工作区版本为 `0.7.3`；读取的是上述 main 提交，不假定 main 与发布标签完全一致。
- 阅读方式：GitHub 连接器核对目录、文档和选定源码片段；未整库复制、部署 Yuxi 或运行其测试。

## 已读来源及参考点

以下链接固定到同一提交；列出的是选定阅读范围，不代表全部分支均已审计。

| 来源 | 确认点或阅读边界 |
| --- | --- |
| [README](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/README.md) | 通用知识智能体平台定位、主要功能、启动方式；没有把其产品效果视为本项目效果 |
| [ARCHITECTURE](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/ARCHITECTURE.md) | API/业务/数据访问边界、请求与 Run 分离、Worker 与状态处理 |
| [docker-compose.yml](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/docker-compose.yml) | API、worker、迁移、存储、沙盒和可选解析服务拓扑 |
| [backend/pyproject.toml](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/pyproject.toml) | 版本、Python 范围、依赖及测试分层配置 |
| [chatbot/graph.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/agents/buildin/chatbot/graph.py) | LangChain create_agent、middleware、工具与 checkpoint 装配，底层框架并非全部由项目自研 |
| [subagent_task.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/agents/middlewares/subagent_task.py) | 子 Agent 的 start/status/cancel/await 及归属检查 |
| [subagent_run_service.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/services/subagent_run_service.py) | 父子运行关系、持久化、先提交再入队；当前子 Agent 不能继续创建子 Agent |
| [subagent/graph.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/agents/buildin/subagent/graph.py) | 子 Agent 工具配置与执行时拒绝边界 |
| [tool_approval.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/agents/tool_approval.py) | 文件/命令审批；有信任模式和路径豁免，不能概括成所有工具每次都审批 |
| [agent_request_service.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/services/agent_request_service.py) | submit_agent_request、_persist_request：作用域检查、保存请求、commit 后 enqueue |
| [agent_request_queue_service.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/services/agent_request_queue_service.py) | recover_pending_dispatches 的 pending/queued 补发片段；未审计完整 FIFO 实现 |
| [agent_run_service.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/services/agent_run_service.py) | enqueue_agent_run、SSE 入口的选定片段 |
| [run_worker.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/services/run_worker.py) | 执行权、heartbeat、取消和 WorkerSettings 等片段 |
| [agent_run_repository.py](https://github.com/xerrors/Yuxi/blob/928141ceb2799cee18bcdbc060618ab9151ba48b/backend/package/yuxi/repositories/agent_run_repository.py) | mark_running 和 reconcile_expired_leases：取得执行权、失联失败收敛 |

另核对了知识库实现、MCP 目录和测试分层的实际文件；没有逐个阅读检索/MCP 实现或运行测试。

## 对本项目的启发与差异

1. 模型提出子任务与确定性后台调度分开。我们的四角色还需有结构化状态、工具权限和停止条件。
2. 先提交数据库事实，再投递队列；M3 要验证保存成功、发布失败的补偿窗口。
3. Run 执行权可约束重复消费，但工单写入仍需要独立的业务幂等与结果保存。
4. 过期 lease 被设为 failed，结果可能未知；不能理解成所有任务都会自动无损恢复。

Yuxi 的功能范围包含知识库、图谱、通用 Agent、Skills/MCP、沙盒和团队治理。本项目围绕技术支持，当前仍为 M0；完成体强调版本证据、角色协作、工单确认与可靠操作。没有移植上游实现，也没有可比较的性能或质量测量。
