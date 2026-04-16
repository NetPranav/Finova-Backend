import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    """
    A 1:1 chat thread between two users.
    Users address each other using their unique Finova IDs (e.g. FHW397 → THT919).
    One conversation per user pair — no duplicates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    participant_one = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_one',
        help_text=_("First participant in the conversation")
    )

    participant_two = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_two',
        help_text=_("Second participant in the conversation")
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-updated_at']
        # Prevent duplicate conversations between the same two users
        constraints = [
            models.UniqueConstraint(
                fields=['participant_one', 'participant_two'],
                name='unique_conversation_pair',
            ),
        ]
        indexes = [
            models.Index(fields=['participant_one', 'updated_at']),
            models.Index(fields=['participant_two', 'updated_at']),
        ]

    def __str__(self):
        return (
            f"Chat: {self.participant_one.username} ↔ "
            f"{self.participant_two.username}"
        )

    def get_other_participant(self, user):
        """Return the other participant in this conversation."""
        if self.participant_one == user:
            return self.participant_two
        return self.participant_one

    @property
    def last_message(self):
        """Return the most recent message in this conversation."""
        return self.direct_messages.order_by('-created_at').first()

    @property
    def unread_count_for(self):
        """
        Get unread count — must be called with a user context.
        Use the view-level helper instead.
        """
        return None  # Handled in serializer with annotation


class DirectMessage(models.Model):
    """
    A single message within a 1:1 conversation.
    Supports text, stock cards (/stocks "AAPL"), and news cards.
    """

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('stock_card', 'Stock Card'),
        ('news_card', 'News Card'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='direct_messages',
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_direct_messages',
    )

    content = models.TextField(
        max_length=5000,
        help_text=_("Message text content")
    )

    message_type = models.CharField(
        max_length=15,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
    )

    stock_symbol = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Stock symbol if message is a stock card (auto-parsed from /stocks template)")
    )

    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_("Reply to another message")
    )

    is_read = models.BooleanField(
        default=False,
        help_text=_("Whether the recipient has read this message")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('direct message')
        verbose_name_plural = _('direct messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"[DM] {self.sender.username}: {self.content[:50]}"

    def save(self, *args, **kwargs):
        # Auto-detect message type from /stocks or /news templates
        if self.message_type == 'text' and self.content:
            from groups.utils import detect_message_type
            msg_type, symbol = detect_message_type(self.content)
            self.message_type = msg_type
            if symbol:
                self.stock_symbol = symbol
        super().save(*args, **kwargs)
