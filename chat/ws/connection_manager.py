from typing import Dict, List
import json
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        # {chat_id: {user_id: websocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        
        self.active_connections[chat_id][user_id] = websocket
    
    def disconnect(self, chat_id: int, user_id: int):
        if chat_id in self.active_connections:
            if user_id in self.active_connections[chat_id]:
                del self.active_connections[chat_id][user_id]
            
            # Clean up empty chat connections
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
    
    async def send_personal_message(self, message: dict, chat_id: int, user_id: int):
        if chat_id in self.active_connections:
            if user_id in self.active_connections[chat_id]:
                websocket = self.active_connections[chat_id][user_id]
                await websocket.send_json(message)
    
    async def broadcast(self, message: dict, chat_id: int, exclude_user_id: int = None):
        if chat_id in self.active_connections:
            for user_id, websocket in self.active_connections[chat_id].items():
                if exclude_user_id is None or user_id != exclude_user_id:
                    await websocket.send_json(message)
    
    def get_active_users_in_chat(self, chat_id: int) -> List[int]:
        if chat_id in self.active_connections:
            return list(self.active_connections[chat_id].keys())
        return []
    
    def is_user_connected(self, chat_id: int, user_id: int) -> bool:
        return (
            chat_id in self.active_connections and 
            user_id in self.active_connections[chat_id]
        )

connection_manager = ConnectionManager()