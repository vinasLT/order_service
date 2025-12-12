from app.rpc_client.auth import AuthRpcClient
from app.rpc_client.gen.python.auth.v1 import auth_pb2


def _build_user_name(user: auth_pb2.GetUserResponse, user_uuid: str) -> str:
    """Build a displayable name from auth service response."""
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(part for part in parts if part).strip()
    if name:
        return name
    if user.username:
        return user.username
    return user_uuid


async def fetch_user_identity(user_uuid: str) -> dict[str, str]:
    async with AuthRpcClient() as auth_client:
        user = await auth_client.get_user(user_uuid=user_uuid)
    return {
        "user_name": _build_user_name(user, user_uuid),
        "user_email": user.email or "",
    }
