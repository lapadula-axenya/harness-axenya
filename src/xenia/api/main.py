"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xenia import __version__
from xenia.agents.registry import get_registry
from xenia.api.deps import get_settings_dep
from xenia.api.middleware.logging import RequestLogMiddleware, configure_logging
from xenia.api.routes import agents, dashboard, processes, runs, webhooks
from xenia.api.schemas import HealthResponse
from xenia.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    configure_logging()
    # Eagerly load registry so YAML errors surface at startup, not at first request.
    get_registry()
    # Phase 4: attach Cloud Monitoring sink to all counters when GCP_PROJECT_ID is set.
    from xenia.observability.metrics import configure_sink

    configure_sink()
    yield


app = FastAPI(
    title="Xenia Harness",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(webhooks.router, prefix="/v1")
app.include_router(runs.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(dashboard.router, prefix="/v1")
app.include_router(processes.router, prefix="/v1")


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
