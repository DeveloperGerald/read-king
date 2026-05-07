from fastapi import FastAPI

from app.core.config import get_settings
from app.api.endpoints import router as api_router


app = FastAPI(title="ReadKing")
app.include_router(api_router)


# 启动时加载配置并放入 app.state，便于路由与服务层复用
@app.on_event("startup")
def startup() -> None:
    app.state.settings = get_settings()


# 健康检查接口：用于验证服务可用与当前 Provider 配置
@app.get("/health")
def health() -> dict:
    settings = getattr(app.state, "settings", None)
    payload: dict = {"status": "ok"}
    if settings is not None:
        payload.update({"llm_provider": settings.llm_provider})
    return payload
