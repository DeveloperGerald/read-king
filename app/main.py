from fastapi import FastAPI

import logging

from app.core.config import get_settings
from app.api.endpoints import router as api_router


app = FastAPI(title="ReadKing")
app.include_router(api_router)


# 启动时加载配置并放入 app.state，便于路由与服务层复用
@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    app.state.settings = settings
    
    # 初始化全局日志配置，确保后台任务日志能在终端输出
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True  # 强制应用配置，防止被其他库提前初始化
    )
    logging.info(f"Logging initialized with level: {settings.log_level.upper()}")


# 健康检查接口：用于验证服务可用与当前 Provider 配置
@app.get("/health")
def health() -> dict:
    settings = getattr(app.state, "settings", None)
    payload: dict = {"status": "ok"}
    if settings is not None:
        payload.update({"llm_provider": settings.llm_provider})
    return payload
