import uuid
import string
import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager


def generate_finova_id():
    """Generate a unique 6-character alphanumeric Finova ID (e.g. FHW397)"""
    chars = string.ascii_uppercase + string.digits
    while True:
        fid = ''.join(random.choices(chars, k=6))
        if not User.objects.filter(finova_id=fid).exists():
            return fid


class User(AbstractUser):
    """
    Custom User model for Finova v2.0
    Supports women-led, inclusive financial education & investing
    """
    
    RANK_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    GENDER_CHOICES = [
        ('woman', 'Woman'),
        ('man',"Man"),
        ('non_binary', 'Non-binary'),
        ('prefer_not_to_say', 'Prefer not to say'),
        ('other', 'Other'),
    ]
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique user identifier"
    )
    
    finova_id = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        help_text=_("Unique 6-char Finova ID (e.g. FHW397) for user lookup")
    )
    
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text="Primary email for login and notifications"
    )
    
    # Personal Information
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    
    date_of_birth = models.DateField(
        null=True, 
        blank=True,
        help_text=_("Used for demographic insights and age verification")
    )
    
    gender_identity = models.CharField(
        max_length=30,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        help_text=_("Self-identified gender")
    )
    
    gender_identity_custom = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("If 'Other' selected, specify here")
    )
    
    # Profile
    profile_picture = models.ImageField(
        upload_to='profile_pictures/%Y/%m/',
        blank=True,
        null=True,
        help_text=_("User avatar image")
    )
    
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text=_("Short bio (max 500 characters)")
    )
    
    # Verification & Security
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Email/identity verified status")
    )
    
    phone_number = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Optional phone for 2FA")
    )
    
    # Financial Information
    individual_virtual_capital = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Individual capital user can allocate to group pools")
    )
    
    # Gamification & Progress
    consensus_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Total trust score across all clubs")
    )
    
    learning_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("Current knowledge tier (1-10)")
    )
    
    user_level = models.CharField(
        max_length=20,
        choices=RANK_CHOICES,
        default='beginner',
        help_text=_("User experience level in trading")
    )
    
    total_reels_watched = models.PositiveIntegerField(
        default=0,
        help_text="Count of Fin-Pulse reels viewed"
    )
    
    total_votes_cast = models.PositiveIntegerField(
        default=0,
        help_text="Total participation in club votes"
    )
    
    # Settings & Preferences
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("User notification settings (email, push, SMS)")
    )
    
    privacy_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Profile visibility and data sharing preferences")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Use email as primary login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['finova_id']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"@{self.username} [{self.finova_id}] ({self.email})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.finova_id:
            self.finova_id = generate_finova_id()
            
        if is_new:
            from decimal import Decimal
            if self.gender_identity == 'woman':
                self.individual_virtual_capital = Decimal('55000.00')
            elif self.gender_identity == 'man':
                self.individual_virtual_capital = Decimal('30000.00')
            else:
                self.individual_virtual_capital = Decimal('30000.00')
                
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        """Return first_name + last_name with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.username
    
    @property
    def age(self):
        """Calculate user age from date_of_birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def display_gender(self):
        """Return readable gender identity"""
        if self.gender_identity == 'other' and self.gender_identity_custom:
            return self.gender_identity_custom
        return self.get_gender_identity_display()
    
    def increment_consensus_score(self, points=1):
        """Add points to user's trust score"""
        self.consensus_score += points
        self.save(update_fields=['consensus_score', 'updated_at'])
    
    def mark_reel_watched(self):
        """Increment reel watch counter"""
        self.total_reels_watched += 1
        self.save(update_fields=['total_reels_watched', 'updated_at'])
    
    def record_vote(self):
        """Increment vote participation counter"""
        self.total_votes_cast += 1
        self.save(update_fields=['total_votes_cast', 'updated_at'])