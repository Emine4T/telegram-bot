class NotificationService:
    def send_notification(self, chat_id: int, message: str) -> str:
        return f"Notification sent to {chat_id}: {message}"
