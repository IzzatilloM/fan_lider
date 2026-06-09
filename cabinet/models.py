from django.db import models


class BotChatState(models.Model):
    """Telegram bot suhbat holati (ro'yxatdan o'tish bosqichlari uchun).

    Webhook stateless bo'lgani uchun foydalanuvchining qaysi bosqichda
    ekanini shu yerda saqlaymiz.
    """
    chat_id = models.CharField(max_length=32, unique=True, db_index=True)
    step = models.CharField(max_length=40, blank=True, default='')
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.chat_id} @ {self.step or 'idle'}"
