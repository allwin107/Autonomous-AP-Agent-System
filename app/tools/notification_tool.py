import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class NotificationTool:
    def __init__(self):
        pass
        
    async def send_notification(self, users: List[str], subject: str, message: str, channels: List[str] = ["email"]):
        """
        Routes notifications to users via specified channels.
        In a real app, this would look up user contact preferences.
        """
        for user in users:
            for channel in channels:
                if channel == "slack":
                    await self._send_slack(user, message)
                elif channel == "email":
                    await self._send_email(user, subject, message)

    async def _send_slack(self, user: str, message: str):
        # Mock Slack API integration
        logger.info(f"[SLACK] To {user}: {message[:50]}...")
        # e.g. slack_client.chat_postMessage(...)

    async def _send_email(self, user: str, subject: str, body: str):
        # Mock Email integration (or use SMTP)
        logger.info(f"[EMAIL] To {user} | Subject: {subject}")
        # e.g. smtp.send_message(...)

notification_tool = NotificationTool()
