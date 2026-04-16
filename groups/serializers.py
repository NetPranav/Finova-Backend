from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Group, GroupMember, GroupMessage,
    Discussion, DiscussionComment, TradePoll, Vote
)

User = get_user_model()


# ──────────────────────── Member Serializers ────────────────────────

class GroupMemberSerializer(serializers.ModelSerializer):
    """Serializer for group membership details."""
    username = serializers.CharField(source='user.username', read_only=True)
    finova_id = serializers.CharField(source='user.finova_id', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    user_level = serializers.CharField(source='user.user_level', read_only=True)

    class Meta:
        model = GroupMember
        fields = [
            'id', 'finova_id', 'username', 'profile_picture',
            'user_level', 'role', 'is_active', 'joined_at',
        ]
        read_only_fields = ['id', 'joined_at']


# ──────────────────────── Group Serializers ────────────────────────

class GroupCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new investment group."""

    class Meta:
        model = Group
        fields = [
            'name', 'description', 'guidelines', 'group_photo',
            'risk_level', 'max_members',
        ]

    def validate_max_members(self, value):
        if value < 2:
            raise serializers.ValidationError("A group must allow at least 2 members.")
        if value > 50:
            raise serializers.ValidationError("A group can have at most 50 members.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        group = Group.objects.create(created_by=user, **validated_data)
        # Creator automatically becomes admin
        GroupMember.objects.create(group=group, user=user, role='admin')
        return group


class GroupListSerializer(serializers.ModelSerializer):
    """Compact serializer for listing groups."""
    member_count = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'finova_id', 'name', 'group_photo', 'risk_level',
            'member_count', 'max_members', 'created_by_username',
            'is_active', 'created_at',
        ]


class GroupDetailSerializer(serializers.ModelSerializer):
    """Full group detail with member list and about section."""
    member_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    members = GroupMemberSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_finova_id = serializers.CharField(source='created_by.finova_id', read_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'finova_id', 'name', 'description', 'guidelines',
            'group_photo', 'risk_level', 'max_members', 'member_count',
            'is_full', 'members', 'created_by', 'created_by_username',
            'created_by_finova_id', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'finova_id', 'created_by', 'created_at', 'updated_at']


class GroupUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admins to update group settings."""

    class Meta:
        model = Group
        fields = [
            'name', 'description', 'guidelines', 'group_photo',
            'risk_level', 'max_members',
        ]


# ──────────────────────── Message Serializers ────────────────────────

class GroupMessageSerializer(serializers.ModelSerializer):
    """Serializer for group chat messages."""
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_finova_id = serializers.CharField(source='sender.finova_id', read_only=True)
    sender_profile_picture = serializers.ImageField(source='sender.profile_picture', read_only=True)

    class Meta:
        model = GroupMessage
        fields = [
            'id', 'group', 'sender', 'sender_username', 'sender_finova_id',
            'sender_profile_picture', 'content', 'message_type',
            'stock_symbol', 'reply_to', 'is_pinned',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'group', 'sender', 'message_type', 'stock_symbol',
            'created_at', 'updated_at',
        ]


class GroupMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for sending a message in a group."""

    class Meta:
        model = GroupMessage
        fields = ['content', 'reply_to']


# ──────────────────────── Discussion Serializers ────────────────────────

class DiscussionCommentSerializer(serializers.ModelSerializer):
    """Serializer for discussion comments."""
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_finova_id = serializers.CharField(source='author.finova_id', read_only=True)

    class Meta:
        model = DiscussionComment
        fields = [
            'id', 'discussion', 'author', 'author_username',
            'author_finova_id', 'content', 'created_at',
        ]
        read_only_fields = ['id', 'discussion', 'author', 'created_at']


class DiscussionCreateSerializer(serializers.ModelSerializer):
    """Serializer for proposing a new stock discussion."""

    class Meta:
        model = Discussion
        fields = [
            'stock_symbol', 'stock_name', 'discussion_type', 'reasoning',
        ]


class DiscussionSerializer(serializers.ModelSerializer):
    """Full discussion detail with engagement tracking."""
    proposed_by_username = serializers.CharField(source='proposed_by.username', read_only=True)
    proposed_by_finova_id = serializers.CharField(source='proposed_by.finova_id', read_only=True)
    can_unlock_voting = serializers.ReadOnlyField()
    comments = DiscussionCommentSerializer(many=True, read_only=True)
    has_poll = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = [
            'id', 'group', 'proposed_by', 'proposed_by_username',
            'proposed_by_finova_id', 'stock_symbol', 'stock_name',
            'discussion_type', 'reasoning', 'status',
            'min_engagement_to_unlock_vote', 'engagement_count',
            'can_unlock_voting', 'has_poll', 'comments',
            'created_at', 'voting_unlocked_at',
        ]
        read_only_fields = [
            'id', 'group', 'proposed_by', 'status',
            'engagement_count', 'created_at', 'voting_unlocked_at',
        ]

    def get_has_poll(self, obj):
        return hasattr(obj, 'poll') and obj.poll is not None


# ──────────────────────── Voting Serializers ────────────────────────

class VoteSerializer(serializers.ModelSerializer):
    """Serializer for casting a vote."""
    voter_username = serializers.CharField(source='voter.username', read_only=True)
    voter_finova_id = serializers.CharField(source='voter.finova_id', read_only=True)

    class Meta:
        model = Vote
        fields = ['id', 'poll', 'voter', 'voter_username', 'voter_finova_id', 'choice', 'cast_at']
        read_only_fields = ['id', 'poll', 'voter', 'cast_at']


class VoteCreateSerializer(serializers.Serializer):
    """Serializer for the vote action."""
    choice = serializers.ChoiceField(choices=['buy', 'sell', 'hold'])


class TradePollSerializer(serializers.ModelSerializer):
    """Full poll details with vote tallies and timer state."""
    total_votes = serializers.ReadOnlyField()
    total_eligible_voters = serializers.ReadOnlyField()
    quorum_met = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    discussion_stock_symbol = serializers.CharField(source='discussion.stock_symbol', read_only=True)
    discussion_type = serializers.CharField(source='discussion.discussion_type', read_only=True)
    votes = VoteSerializer(many=True, read_only=True)

    class Meta:
        model = TradePoll
        fields = [
            'id', 'discussion', 'discussion_stock_symbol', 'discussion_type',
            'quorum_percentage', 'voting_deadline', 'original_deadline',
            'reduced_deadline', 'turbo_reduction_applied', 'status',
            'result_buy_count', 'result_sell_count', 'result_hold_count',
            'total_votes', 'total_eligible_voters', 'quorum_met', 'is_expired',
            'votes', 'created_at', 'resolved_at',
        ]
        read_only_fields = '__all__'
