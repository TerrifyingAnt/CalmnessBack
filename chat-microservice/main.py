from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from api import api_router
from core.config import settings
from websockets.chat_ws import chat_endpoint
from core.database import Base, async_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

app = FastAPI(title=settings.PROJECT_NAME)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify your allowed origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket endpoints
@app.websocket("/ws/chat/{chat_id}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    chat_id: int, 
    user_id: int
):
    await chat_endpoint(websocket, chat_id, user_id)

@app.on_event("startup")
async def startup():
    # Create tables if they don't exist
    async with async_engine.begin() as conn:
        # Uncomment to create tables on startup
        # await conn.run_sync(Base.metadata.create_all)
        pass
    logging.info("Application startup complete")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)