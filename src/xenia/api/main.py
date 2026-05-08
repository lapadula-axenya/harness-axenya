"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from xenia import __version__
from xenia.agents.registry import get_registry
from xenia.api.deps import get_settings_dep
from xenia.api.middleware.logging import RequestLogMiddleware, configure_logging
from xenia.api.routes import agents, dashboard, runs, webhooks
from xenia.api.schemas import HealthResponse
from xenia.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    configure_logging()
    # Eagerly load registry so YAML errors surface at startup, not at first request.
    get_registry()
    yield


app = FastAPI(
    title="Xenia Harness",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(RequestLogMiddleware)

app.include_router(webhooks.router, prefix="/v1")
app.include_router(runs.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(dashboard.router, prefix="/v1")


@app.get("/health", response_model=HealthResponse)
async def health(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=__version__,
        env=settings.env,
    )
