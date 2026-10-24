from typing import Annotated
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse

from support_app.models import SupportRequest, SupportResponse
from support_app.security import Principal, get_principal
from support_app.service import SupportService
from support_app.tools import ExecutionPolicy, MockReadTools, ReadTools


def create_app(
    tools: ReadTools | None = None, policy: ExecutionPolicy | None = None,
) -> FastAPI:
    app = FastAPI(
        title="NimbusDesk 技术支持 · M0 模拟业务基线",
        version="0.1.0",
        description="规则路由及本地模拟只读工具；未接模型、持久化或工单执行。",
        swagger_ui_parameters={"persistAuthorization": False},
    )
    service = SupportService(tools or MockReadTools(), policy or ExecutionPolicy())
    demo_html = Path(__file__).with_name("demo.html").read_text(encoding="utf-8")

    @app.get("/", include_in_schema=False)
    async def home() -> HTMLResponse:
        return HTMLResponse(demo_html)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "mode": "mock", "milestone": "M0", "persistence": False}

    @app.post("/api/support", response_model=SupportResponse)
    async def submit_support(
        request: SupportRequest,
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> SupportResponse:
        return await service.handle(request, principal)

    return app


app = create_app()
