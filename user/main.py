from fastapi import FastAPI
from core.config import settings
from api import user

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(user.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
