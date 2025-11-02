"""Event manager for Server-Sent Events (SSE) notifications."""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventManager:
    """Manager for SSE event broadcasting to connected clients."""
    
    def __init__(self):
        """Initialize event manager with subscriber tracking."""
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(self, user_id: str, queue: asyncio.Queue):
        """Subscribe a client to receive events for a user.
        
        Args:
            user_id: User ID to subscribe to
            queue: Queue to send events to
        """
        async with self._lock:
            if user_id not in self.subscribers:
                self.subscribers[user_id] = []
            self.subscribers[user_id].append(queue)
            logger.info(f"Client subscribed to events for user {user_id}")
    
    async def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """Unsubscribe a client from receiving events.
        
        Args:
            user_id: User ID to unsubscribe from
            queue: Queue to remove
        """
        async with self._lock:
            if user_id in self.subscribers:
                try:
                    self.subscribers[user_id].remove(queue)
                    if not self.subscribers[user_id]:
                        del self.subscribers[user_id]
                    logger.info(f"Client unsubscribed from events for user {user_id}")
                except ValueError:
                    pass
    
    async def broadcast_event(
        self,
        user_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Broadcast an event to all subscribers of a user.
        
        Args:
            user_id: User ID to broadcast to
            event_type: Type of event (game_completed, session_finished, etc.)
            data: Event data payload
        """
        async with self._lock:
            subscribers = self.subscribers.get(user_id, [])
        
        if not subscribers:
            logger.debug(f"No subscribers for user {user_id}, skipping broadcast")
            return
        
        event = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        # Send to all subscribers
        dead_queues = []
        for queue in subscribers:
            try:
                await asyncio.wait_for(queue.put(event), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending event to subscriber for user {user_id}")
                dead_queues.append(queue)
            except Exception as e:
                logger.error(f"Error sending event to subscriber: {e}")
                dead_queues.append(queue)
        
        # Clean up dead queues
        if dead_queues:
            async with self._lock:
                for queue in dead_queues:
                    try:
                        self.subscribers[user_id].remove(queue)
                    except (ValueError, KeyError):
                        pass
                if user_id in self.subscribers and not self.subscribers[user_id]:
                    del self.subscribers[user_id]
        
        logger.info(f"Broadcasted {event_type} event to {len(subscribers) - len(dead_queues)} subscribers for user {user_id}")
    
    async def get_subscriber_count(self, user_id: Optional[str] = None) -> int:
        """Get number of active subscribers.
        
        Args:
            user_id: Optional user ID to count subscribers for
            
        Returns:
            Number of active subscribers
        """
        async with self._lock:
            if user_id:
                return len(self.subscribers.get(user_id, []))
            return sum(len(queues) for queues in self.subscribers.values())


# Global event manager instance
event_manager = EventManager()
