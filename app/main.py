from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import shutdown_job_manager
from app.api.errors import register_error_handlers
from app.api.routes import router
from app.frontend import mount_frontend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    shutdown_job_manager()


app = FastAPI(title="Drive-to-Text", version="0.1.0", lifespan=lifespan)
app.include_router(router)
register_error_handlers(app)
mount_frontend(app)  # last, so the /api routes above keep priority
