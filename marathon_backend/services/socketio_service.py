"""
Socket.IO Service - Real-time event management for Marathon Backend

Provides centralized Socket.IO event emission for Gmail, job applications,
and other real-time updates.
"""
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global reference to Socket.IO server (set during app initialization)
_sio_server = None


def initialize_socketio(sio):
    """Initialize the Socket.IO service with server instance."""
    global _sio_server
    _sio_server = sio
    logger.info("Socket.IO service initialized")


def get_sio():
    """Get the Socket.IO server instance."""
    return _sio_server


async def emit_gmail_update(user_id: str, update_type: str, data: Dict[str, Any]):
    """
    Emit Gmail update to all connected clients for a user.
    
    Args:
        user_id: The user ID to send the update to
        update_type: Type of update (new_email, drafts_updated, etc.)
        data: The update data payload
    """
    if not _sio_server:
        logger.warning("Socket.IO server not initialized, skipping emit")
        return
    
    event_name = f"gmail_update_{user_id}"
    payload = {
        "type": update_type,
        **data
    }
    
    logger.info(f"Emitting {event_name}: {update_type}")
    await _sio_server.emit(event_name, payload)


async def emit_job_update(user_id: str, update_type: str, data: Dict[str, Any]):
    """
    Emit job application update to all connected clients for a user.
    
    Args:
        user_id: The user ID to send the update to
        update_type: Type of update (status_changed, new_match, etc.)
        data: The update data payload
    """
    if not _sio_server:
        logger.warning("Socket.IO server not initialized, skipping emit")
        return
    
    event_name = f"job_update_{user_id}"
    payload = {
        "type": update_type,
        **data
    }
    
    logger.info(f"Emitting {event_name}: {update_type}")
    await _sio_server.emit(event_name, payload)


async def emit_campaign_update(user_id: str, campaign_id: str, update_type: str, data: Dict[str, Any]):
    """
    Emit campaign update to all connected clients.
    
    Args:
        user_id: The user ID
        campaign_id: The campaign ID
        update_type: Type of update (status_changed, results_updated, etc.)
        data: The update data payload
    """
    if not _sio_server:
        logger.warning("Socket.IO server not initialized, skipping emit")
        return
    
    event_name = f"campaign_update_{user_id}_{campaign_id}"
    payload = {
        "type": update_type,
        **data
    }
    
    logger.info(f"Emitting {event_name}: {update_type}")
    await _sio_server.emit(event_name, payload)


async def broadcast_to_user(user_id: str, event_name: str, data: Dict[str, Any]):
    """
    Broadcast any event to a specific user.
    
    Args:
        user_id: The user ID
        event_name: The event name
        data: The event data
    """
    if not _sio_server:
        logger.warning("Socket.IO server not initialized, skipping emit")
        return
    
    logger.info(f"Broadcasting {event_name} to user {user_id}")
    await _sio_server.emit(f"{event_name}_{user_id}", data)
