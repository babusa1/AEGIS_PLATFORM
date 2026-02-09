"""
WebSocket Real-Time Communication

WebSocket handler for real-time Cowork sessions.
Provides:
- Real-time state synchronization
- Message broadcasting
- Typing indicators
- Presence (who's in session)
- Conflict resolution (concurrent edits)
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect
import structlog

from aegis.cowork.engine import CoworkEngine

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for Cowork sessions.
    
    Features:
    - Multiple users per session
    - Message broadcasting
    - Presence tracking
    - Typing indicators
    """
    
    def __init__(self):
        # session_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> session_id, user_id
        self.connection_info: Dict[WebSocket, Dict[str, str]] = {}
        # session_id -> Set of user_ids (presence)
        self.session_presence: Dict[str, Set[str]] = {}
        # user_id -> typing status
        self.typing_status: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """
        Connect a user to a Cowork session.
        
        Args:
            websocket: WebSocket connection
            session_id: Session ID
            user_id: User ID
        """
        await websocket.accept()
        
        # Add to active connections
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        
        # Store connection info
        self.connection_info[websocket] = {
            "session_id": session_id,
            "user_id": user_id,
        }
        
        # Update presence
        if session_id not in self.session_presence:
            self.session_presence[session_id] = set()
        self.session_presence[session_id].add(user_id)
        
        logger.info(
            "WebSocket connected",
            session_id=session_id,
            user_id=user_id,
            total_connections=len(self.active_connections[session_id]),
        )
        
        # Broadcast presence update
        await self.broadcast_presence(session_id)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a user from a session."""
        if websocket not in self.connection_info:
            return
        
        info = self.connection_info[websocket]
        session_id = info["session_id"]
        user_id = info["user_id"]
        
        # Remove from active connections
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        # Remove connection info
        del self.connection_info[websocket]
        
        # Update presence
        if session_id in self.session_presence:
            self.session_presence[session_id].discard(user_id)
            if not self.session_presence[session_id]:
                del self.session_presence[session_id]
        
        logger.info(
            "WebSocket disconnected",
            session_id=session_id,
            user_id=user_id,
        )
        
        # Broadcast presence update (async, but don't await)
        asyncio.create_task(self.broadcast_presence(session_id))
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
    
    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_websocket: Optional[WebSocket] = None,
    ):
        """
        Broadcast message to all connections in a session.
        
        Args:
            session_id: Session ID
            message: Message to broadcast
            exclude_websocket: Optional WebSocket to exclude from broadcast
        """
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[session_id]:
            if websocket == exclude_websocket:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to broadcast message", error=str(e))
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_presence(self, session_id: str):
        """Broadcast presence update to session."""
        if session_id not in self.session_presence:
            return
        
        user_ids = list(self.session_presence[session_id])
        
        message = {
            "type": "presence_update",
            "session_id": session_id,
            "users": user_ids,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.broadcast_to_session(session_id, message)
    
    async def set_typing(
        self,
        session_id: str,
        user_id: str,
        is_typing: bool,
    ):
        """Set typing status for a user."""
        self.typing_status[user_id] = {
            "session_id": session_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        message = {
            "type": "typing",
            "session_id": session_id,
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.broadcast_to_session(session_id, message)


# Global connection manager
connection_manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str,
    cowork_engine: CoworkEngine,
):
    """
    WebSocket endpoint for Cowork sessions.
    
    Handles:
    - Real-time state synchronization
    - Message broadcasting
    - Typing indicators
    - Presence updates
    """
    await connection_manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                # Handle chat message
                content = data.get("content", "")
                
                # Add message to session
                session = await cowork_engine.get_session(session_id)
                if session:
                    session.add_message(
                        role="user",
                        content=content,
                        user_id=user_id,
                    )
                    await cowork_engine._save_session(session)
                
                # Broadcast message
                await connection_manager.broadcast_to_session(
                    session_id,
                    {
                        "type": "message",
                        "user_id": user_id,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    exclude_websocket=websocket,
                )
            
            elif message_type == "typing":
                # Handle typing indicator
                is_typing = data.get("is_typing", False)
                await connection_manager.set_typing(session_id, user_id, is_typing)
            
            elif message_type == "artifact_update":
                # Handle artifact update
                artifact_id = data.get("artifact_id")
                updates = data.get("updates", {})
                
                # Update artifact in session
                session = await cowork_engine.get_session(session_id)
                if session:
                    await cowork_engine.update_artifact(
                        session_id,
                        artifact_id,
                        updates,
                        edited_by=user_id,
                    )
                
                # Broadcast update
                await connection_manager.broadcast_to_session(
                    session_id,
                    {
                        "type": "artifact_update",
                        "artifact_id": artifact_id,
                        "user_id": user_id,
                        "updates": updates,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    exclude_websocket=websocket,
                )
            
            elif message_type == "state_sync":
                # Handle state synchronization request
                session = await cowork_engine.get_session(session_id)
                if session:
                    await connection_manager.send_personal_message(
                        {
                            "type": "state_sync",
                            "session_id": session_id,
                            "state": session.state.model_dump(mode="json"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        websocket,
                    )
            
            elif message_type == "ping":
                # Handle ping (keep-alive)
                await connection_manager.send_personal_message(
                    {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    websocket,
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info("WebSocket disconnected", session_id=session_id, user_id=user_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id, user_id=user_id)
        connection_manager.disconnect(websocket)
