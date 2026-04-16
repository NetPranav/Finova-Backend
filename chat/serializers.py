from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Conversation, DirectMessage

User = get_user_model()


# ──────────────────────── Message Serializers ────────────────────────

class DirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for direct messages with sender info."""
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_finova_id = serializers.CharField(source='sender.finova_id', read_only=True)
    sender_profile_picture = serializers.ImageField(
        source='sender.profile_picture', read_only=True
    )

    class Meta:
        model = DirectMessage
        fields = [
            'id', 'conversation', 'sender', 'sender_username',
            'sender_finova_id', 'sender_profile_picture',
            'content', 'message_type', 'stock_symbol',
            'reply_to', 'is_read', 'created_at',
        ]
        read_only_fields = [
            'id', 'conversation', 'sender', 'message_type',
            'stock_symbol', 'created_at',
        ]


class DirectMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for sending a direct message."""

    class Meta:
        model = DirectMessage
        fields = ['content', 'reply_to']


# ──────────────────────── Conversation Serializers ────────────────────────

class ConversationListSerializer(serializers.ModelSerializer):
    """
    Compact conversation serializer for the chat list.
    Shows the other participant's info + last message preview + unread count.
    """
    other_user_username = serializers.SerializerMethodField()
    other_user_finova_id = serializers.SerializerMethodField()
    other_user_profile_picture = serializers.SerializerMethodField()
    other_user_user_level = serializers.SerializerMethodField()
    last_message_content = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    last_message_sender_finova_id = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'other_user_username', 'other_user_finova_id',
            'other_user_profile_picture', 'other_user_user_level',
            'last_message_content', 'last_message_time',
            'last_message_sender_finova_id', 'unread_count',
            'created_at', 'updated_at',
        ]

    def _get_other_user(self, obj):
        request_user = self.context['request'].user
        if obj.participant_one == request_user:
            return obj.participant_two
        return obj.participant_one

    def get_other_user_username(self, obj):
        return self._get_other_user(obj).username

    def get_other_user_finova_id(self, obj):
        return self._get_other_user(obj).finova_id

    def get_other_user_profile_picture(self, obj):
        user = self._get_other_user(obj)
        if user.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user.profile_picture.url)
            return user.profile_picture.url
        return None

    def get_other_user_user_level(self, obj):
        return self._get_other_user(obj).user_level

    def get_last_message_content(self, obj):
        msg = obj.direct_messages.order_by('-created_at').first()
        if msg:
            return msg.content[:100]
        return None

    def get_last_message_time(self, obj):
        msg = obj.direct_messages.order_by('-created_at').first()
        if msg:
            return msg.created_at
        return obj.created_at

    def get_last_message_sender_finova_id(self, obj):
        msg = obj.direct_messages.order_by('-created_at').first()
        if msg:
            return msg.sender.finova_id
        return None

    def get_unread_count(self, obj):
        request_user = self.context['request'].user
        return obj.direct_messages.filter(is_read=False).exclude(
            sender=request_user
        ).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Full conversation detail with participant info."""
    participant_one_username = serializers.CharField(
        source='participant_one.username', read_only=True
    )
    participant_one_finova_id = serializers.CharField(
        source='participant_one.finova_id', read_only=True
    )
    participant_two_username = serializers.CharField(
        source='participant_two.username', read_only=True
    )
    participant_two_finova_id = serializers.CharField(
        source='participant_two.finova_id', read_only=True
    )

    class Meta:
        model = Conversation
        fields = [
            'id', 'participant_one', 'participant_one_username',
            'participant_one_finova_id', 'participant_two',
            'participant_two_username', 'participant_two_finova_id',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = '__all__'


class StartConversationSerializer(serializers.Serializer):
    """Serializer for starting a new conversation by Finova ID."""
    finova_id = serializers.CharField(
        max_length=6,
        help_text="The Finova ID of the user to chat with (e.g. THT919)"
    )

    def validate_finova_id(self, value):
        value = value.upper().strip()
        try:
            target_user = User.objects.get(finova_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f"No user found with Finova ID '{value}'."
            )

        request_user = self.context['request'].user
        if target_user == request_user:
            raise serializers.ValidationError("You cannot start a conversation with yourself.")

        return value
