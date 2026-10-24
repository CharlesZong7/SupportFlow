from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# Fictional catalog and PUBLIC local-demo credentials, never production auth.
CATALOG = {"nimbusdesk": frozenset({"1.0", "1.1"})}


@dataclass(frozen=True)
class Principal:
    user_id: str
    grants: frozenset[tuple[str, str]]


DEMO_IDENTITIES = {
    "dev-alice": Principal("demo-alice", frozenset({
        ("nimbusdesk", "1.0"), ("nimbusdesk", "1.1"),
    })),
    "dev-bob": Principal("demo-bob", frozenset({("nimbusdesk", "1.0")})),
}
bearer = HTTPBearer(auto_error=False)


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    principal = DEMO_IDENTITIES.get(credentials.credentials) if credentials else None
    if principal is None:
        raise HTTPException(401, "需要有效的本地演示 Bearer 凭据。", headers={
            "WWW-Authenticate": "Bearer",
        })
    return principal


def validate_scope(
    principal: Principal, product: str | None, version: str | None,
) -> None:
    """Validate supplied scope before routing; tools repeat this check."""
    if product is None:
        return
    if product not in CATALOG:
        raise HTTPException(400, "未知产品；M0 仅支持 nimbusdesk。")
    if not any(grant[0] == product for grant in principal.grants):
        raise HTTPException(403, "无该产品访问权限。")
    if version is None:
        return
    if version not in CATALOG[product]:
        raise HTTPException(400, "未知版本；不自动使用其他版本资料。")
    if (product, version) not in principal.grants:
        raise HTTPException(403, "无该产品版本的访问权限。")

