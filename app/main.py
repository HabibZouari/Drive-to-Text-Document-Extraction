from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router

app = FastAPI(title="Drive-to-Text", version="0.1.0")
app.include_router(router)
register_error_handlers(app)
