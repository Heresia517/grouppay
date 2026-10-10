"""WebSocket consumer pour les notifications."""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer WebSocket pour un utilisateur authentifie."""

    async def connect(self):
        user = self.scope.get("user")

        # Verifier auth
        if not user or not user.is_authenticated:
            logger.warning("WebSocket: connexion anonyme rejetee")
            await self.close(code=4001)
            return

        self.group_name = f"notif_{user.id}"

        # Rejoindre le groupe
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket: {user.email} connecte au groupe {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"WebSocket: deconnecte ({close_code})")

    async def notify(self, event):
        """Envoie une notification au client."""
        await self.send(text_data=json.dumps(event["payload"]))

    async def receive(self, text_data):
        """Reception d'un message (ping)."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except Exception:
            pass
