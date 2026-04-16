import uuid
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Group(models.Model):
    """
    Investment Group — A small club (5-10 people) that pools simulated capital,
    discusses stocks, and votes on trades via the consensus protocol.
    Like a WhatsApp group but built for collaborative investing.
    """

    RISK_LEVEL_CHOICES = [
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    finova_id = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        help_text=_("Unique group ID (e.g. GRP-A4F821)")
    )

    name = models.CharField(
        max_length=100,
        help_text=_("Group name")
    )

    description = models.TextField(
        max_length=1000,
        blank=True,
        help_text=_("Group description for the about section")
    )

    guidelines = models.TextField(
        max_length=2000,
        blank=True,
        help_text=_("Group rules & investment guidelines")
    )

    group_photo = models.ImageField(
        upload_to='group_photos/%Y/%m/',
        blank=True,
        null=True,
        help_text=_("Group avatar/photo")
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='moderate',
        help_text=_("Risk assessment level for this group")
    )

    max_members = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(2), MaxValueValidator(50)],
        help_text=_("Maximum number of members allowed (2-50)")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups',
        help_text=_("User who created this group")
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['finova_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} [{self.finova_id}]"

    def save(self, *args, **kwargs):
        if not self.finova_id:
            from .utils import generate_group_finova_id
            self.finova_id = generate_group_finova_id()
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.members.filter(is_active=True).count()

    @property
    def is_full(self):
        return self.member_count >= self.max_members


class GroupMember(models.Model):
    """
    Membership record linking a user to a group with a specific role.
    One user can be a member of multiple groups, but only one membership per group.
    """

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='member',
        help_text=_("Member role within the group")
    )

    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('group member')
        verbose_name_plural = _('group members')
        unique_together = ['group', 'user']
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class GroupMessage(models.Model):
    """
    A message sent within a group chat.
    Supports text, stock cards (via /stocks template), news cards, and system messages.
    """

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('stock_card', 'Stock Card'),
        ('news_card', 'News Card'),
        ('system', 'System Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='messages',
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_messages',
        null=True,
        blank=True,
        help_text=_("Null for system messages")
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
        help_text=_("Reply thread parent message")
    )

    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('group message')
        verbose_name_plural = _('group messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'created_at']),
            models.Index(fields=['message_type']),
        ]

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'SYSTEM'
        return f"[{self.group.name}] {sender_name}: {self.content[:50]}"

    def save(self, *args, **kwargs):
        # Auto-detect message type from /stocks or /news templates
        if self.message_type == 'text' and self.content:
            from .utils import detect_message_type
            msg_type, symbol = detect_message_type(self.content)
            self.message_type = msg_type
            if symbol:
                self.stock_symbol = symbol
        super().save(*args, **kwargs)


class Discussion(models.Model):
    """
    Discussion-to-Poll Pipeline: A user proposes a stock to the group for debate.
    Once enough members engage (comment), the discussion unlocks for formal voting.
    """

    STATUS_CHOICES = [
        ('open', 'Open for Discussion'),
        ('voting', 'Voting in Progress'),
        ('executed', 'Trade Executed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected by Vote'),
    ]

    DISCUSSION_TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='discussions',
    )

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proposed_discussions',
    )

    stock_symbol = models.CharField(
        max_length=20,
        help_text=_("Ticker symbol (e.g. AAPL, RELIANCE)")
    )

    stock_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Full company name")
    )

    discussion_type = models.CharField(
        max_length=10,
        choices=DISCUSSION_TYPE_CHOICES,
        help_text=_("Proposed action: buy, sell, or hold")
    )

    reasoning = models.TextField(
        max_length=5000,
        help_text=_("Why the proposer thinks this trade should happen")
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open',
    )

    min_engagement_to_unlock_vote = models.PositiveIntegerField(
        default=3,
        help_text=_("Minimum number of member comments before voting unlocks")
    )

    engagement_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Current number of comments on this discussion")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    voting_unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('discussion')
        verbose_name_plural = _('discussions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['stock_symbol']),
        ]

    def __str__(self):
        return f"[{self.group.name}] {self.discussion_type.upper()} {self.stock_symbol} by {self.proposed_by.username}"

    @property
    def can_unlock_voting(self):
        return (
            self.status == 'open'
            and self.engagement_count >= self.min_engagement_to_unlock_vote
        )

    def unlock_voting(self):
        """Transition from discussion to voting phase, creating a TradePoll."""
        if not self.can_unlock_voting:
            return None
        self.status = 'voting'
        self.voting_unlocked_at = timezone.now()
        self.save(update_fields=['status', 'voting_unlocked_at'])

        poll = TradePoll.objects.create(
            discussion=self,
            voting_deadline=timezone.now() + timezone.timedelta(hours=24),
            original_deadline=timezone.now() + timezone.timedelta(hours=24),
        )
        return poll


class DiscussionComment(models.Model):
    """
    Comments on a discussion. Each comment increments the discussion's engagement_count,
    which determines when voting unlocks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name='comments',
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussion_comments',
    )

    content = models.TextField(
        max_length=2000,
        help_text=_("Comment text")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('discussion comment')
        verbose_name_plural = _('discussion comments')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} on {self.discussion.stock_symbol}: {self.content[:50]}"


class TradePoll(models.Model):
    """
    Voting poll created when a Discussion unlocks.
    Implements the Hybrid State-Machine:
      - Standard mode: 60% quorum within 24 hours
      - Turbo-Reduction: if 100% vote, timer reduces by 90%
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    discussion = models.OneToOneField(
        Discussion,
        on_delete=models.CASCADE,
        related_name='poll',
    )

    quorum_percentage = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_("Percentage of members needed to approve (default 60%)")
    )

    voting_deadline = models.DateTimeField(
        help_text=_("Current deadline (may be reduced by Turbo mode)")
    )

    original_deadline = models.DateTimeField(
        help_text=_("Original 24-hour deadline before any Turbo reduction")
    )

    reduced_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Deadline after Turbo-Reduction (90% time drop)")
    )

    turbo_reduction_applied = models.BooleanField(
        default=False,
        help_text=_("Whether 100% participation triggered Turbo mode")
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
    )

    # Vote tallies (updated on each vote)
    result_buy_count = models.PositiveIntegerField(default=0)
    result_sell_count = models.PositiveIntegerField(default=0)
    result_hold_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('trade poll')
        verbose_name_plural = _('trade polls')
        ordering = ['-created_at']

    def __str__(self):
        return f"Poll for {self.discussion.stock_symbol} ({self.status})"

    @property
    def total_votes(self):
        return self.result_buy_count + self.result_sell_count + self.result_hold_count

    @property
    def total_eligible_voters(self):
        return self.discussion.group.members.filter(is_active=True).count()

    @property
    def is_expired(self):
        return timezone.now() > self.voting_deadline

    @property
    def quorum_met(self):
        if self.total_eligible_voters == 0:
            return False
        return (self.total_votes / self.total_eligible_voters * 100) >= self.quorum_percentage

    def apply_turbo_reduction(self):
        """
        If 100% of members have voted, reduce the remaining time by 90%.
        e.g., 24 hours remaining → 2.4 hours remaining.
        Does NOT execute instantly — ensures a cool-down period.
        """
        if self.turbo_reduction_applied:
            return
        if self.total_votes >= self.total_eligible_voters and self.total_eligible_voters > 0:
            now = timezone.now()
            remaining = self.voting_deadline - now
            if remaining.total_seconds() > 0:
                reduced_seconds = remaining.total_seconds() * 0.1  # Keep only 10%
                self.reduced_deadline = now + timezone.timedelta(seconds=reduced_seconds)
                self.voting_deadline = self.reduced_deadline
                self.turbo_reduction_applied = True
                self.save(update_fields=[
                    'voting_deadline', 'reduced_deadline', 'turbo_reduction_applied'
                ])

    def resolve(self):
        """Determine the outcome of the poll and update the related discussion."""
        if self.status != 'active':
            return

        if self.is_expired and not self.quorum_met:
            self.status = 'expired'
            self.discussion.status = 'expired'
        elif self.quorum_met:
            # Determine winning action
            votes = {
                'buy': self.result_buy_count,
                'sell': self.result_sell_count,
                'hold': self.result_hold_count,
            }
            winner = max(votes, key=votes.get)
            if votes[winner] > 0:
                self.status = 'passed'
                self.discussion.status = 'executed'
            else:
                self.status = 'failed'
                self.discussion.status = 'rejected'
        else:
            return  # Not yet expired or quorum met

        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])
        self.discussion.save(update_fields=['status'])


class Vote(models.Model):
    """
    Individual vote cast by a group member on a TradePoll.
    Each user can only vote once per poll.
    """

    CHOICE_OPTIONS = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    poll = models.ForeignKey(
        TradePoll,
        on_delete=models.CASCADE,
        related_name='votes',
    )

    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trade_votes',
    )

    choice = models.CharField(
        max_length=10,
        choices=CHOICE_OPTIONS,
    )

    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('vote')
        verbose_name_plural = _('votes')
        unique_together = ['poll', 'voter']
        ordering = ['cast_at']

    def __str__(self):
        return f"{self.voter.username} voted {self.choice} on {self.poll.discussion.stock_symbol}"
