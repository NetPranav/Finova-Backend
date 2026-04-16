from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Group, GroupMember, GroupMessage,
    Discussion, DiscussionComment, TradePoll, Vote,
)
from .serializers import (
    GroupCreateSerializer, GroupListSerializer, GroupDetailSerializer,
    GroupUpdateSerializer, GroupMemberSerializer,
    GroupMessageSerializer, GroupMessageCreateSerializer,
    DiscussionSerializer, DiscussionCreateSerializer,
    DiscussionCommentSerializer,
    TradePollSerializer, VoteCreateSerializer, VoteSerializer,
)
from .permissions import IsGroupMember, IsGroupAdmin


# ──────────────────── Helper Mixin ────────────────────

class GroupLookupMixin:
    """Mixin to resolve a group from the URL's finova_id kwarg."""

    def get_group(self):
        finova_id = self.kwargs.get('group_finova_id')
        if not finova_id:
            return None
        return get_object_or_404(Group, finova_id=finova_id, is_active=True)


# ──────────────────── Group CRUD ────────────────────

class GroupViewSet(viewsets.ModelViewSet):
    """
    Investment Group management.

    POST   /api/groups/                         — create a new group
    GET    /api/groups/                         — list your groups
    GET    /api/groups/{finova_id}/              — group detail (about)
    PATCH  /api/groups/{finova_id}/              — update group settings (admin)
    DELETE /api/groups/{finova_id}/              — deactivate group (admin)
    POST   /api/groups/{finova_id}/join/         — join a group
    POST   /api/groups/{finova_id}/leave/        — leave a group
    GET    /api/groups/{finova_id}/members/       — list members
    PATCH  /api/groups/{finova_id}/promote/       — promote/demote member (admin)
    POST   /api/groups/{finova_id}/kick/          — kick member (admin)
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'finova_id'

    def get_queryset(self):
        user = self.request.user
        if self.action == 'list':
            # Show groups where the user is a member
            return Group.objects.filter(
                members__user=user, members__is_active=True, is_active=True
            ).distinct()
        return Group.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        elif self.action == 'list':
            return GroupListSerializer
        elif self.action in ['update', 'partial_update']:
            return GroupUpdateSerializer
        return GroupDetailSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsGroupAdmin()]
        return super().get_permissions()

    def get_group(self):
        """For permission classes that need group context."""
        finova_id = self.kwargs.get('finova_id') or self.kwargs.get('pk')
        if finova_id:
            return Group.objects.filter(finova_id=finova_id, is_active=True).first()
        return None

    def perform_destroy(self, instance):
        """Soft-delete: deactivate instead of deleting."""
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    # ── Join / Leave ──

    @action(detail=True, methods=['post'])
    def join(self, request, finova_id=None):
        """Join a group by its Finova ID."""
        group = self.get_object()

        if group.is_full:
            return Response(
                {"error": f"Group is full ({group.member_count}/{group.max_members})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership, created = GroupMember.objects.get_or_create(
            group=group, user=request.user,
            defaults={'role': 'member'},
        )

        if not created and membership.is_active:
            return Response(
                {"error": "You are already a member of this group."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif not created:
            # Re-activate if previously left
            membership.is_active = True
            membership.save(update_fields=['is_active'])

        return Response(
            {"message": f"Joined {group.name} successfully.", "group_finova_id": group.finova_id},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, finova_id=None):
        """Leave a group."""
        group = self.get_object()
        membership = GroupMember.objects.filter(
            group=group, user=request.user, is_active=True
        ).first()

        if not membership:
            return Response(
                {"error": "You are not a member of this group."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if membership.role == 'admin' and group.members.filter(role='admin', is_active=True).count() <= 1:
            return Response(
                {"error": "You are the only admin. Transfer admin role before leaving."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.is_active = False
        membership.save(update_fields=['is_active'])

        return Response(
            {"message": f"Left {group.name} successfully."},
            status=status.HTTP_200_OK,
        )

    # ── Member Management ──

    @action(detail=True, methods=['get'])
    def members(self, request, finova_id=None):
        """List all active members of a group."""
        group = self.get_object()
        members = group.members.filter(is_active=True).select_related('user')
        serializer = GroupMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='promote')
    def promote(self, request, finova_id=None):
        """
        Promote or demote a member. Admin only.
        Body: { "user_finova_id": "ABC123", "role": "moderator" }
        """
        group = self.get_object()
        admin_membership = group.members.filter(
            user=request.user, role='admin', is_active=True
        ).first()
        if not admin_membership:
            return Response(
                {"error": "Only admins can promote or demote members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_finova_id = request.data.get('user_finova_id')
        new_role = request.data.get('role')

        if new_role not in ['admin', 'moderator', 'member']:
            return Response(
                {"error": "Role must be 'admin', 'moderator', or 'member'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        target_user = User.objects.filter(finova_id=user_finova_id).first()
        if not target_user:
            return Response(
                {"error": f"User {user_finova_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = group.members.filter(user=target_user, is_active=True).first()
        if not membership:
            return Response(
                {"error": "User is not an active member of this group."},
                status=status.HTTP_404_NOT_FOUND,
            )

        membership.role = new_role
        membership.save(update_fields=['role'])

        return Response({
            "message": f"{target_user.username} is now {new_role} in {group.name}.",
        })

    @action(detail=True, methods=['post'], url_path='kick')
    def kick(self, request, finova_id=None):
        """
        Kick a member from the group. Admin only.
        Body: { "user_finova_id": "ABC123" }
        """
        group = self.get_object()
        admin_membership = group.members.filter(
            user=request.user, role='admin', is_active=True
        ).first()
        if not admin_membership:
            return Response(
                {"error": "Only admins can kick members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_finova_id = request.data.get('user_finova_id')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target_user = User.objects.filter(finova_id=user_finova_id).first()
        if not target_user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user == request.user:
            return Response({"error": "You cannot kick yourself."}, status=status.HTTP_400_BAD_REQUEST)

        membership = group.members.filter(user=target_user, is_active=True).first()
        if not membership:
            return Response({"error": "User is not in this group."}, status=status.HTTP_404_NOT_FOUND)

        membership.is_active = False
        membership.save(update_fields=['is_active'])

        return Response({"message": f"{target_user.username} has been removed from {group.name}."})


# ──────────────────── Group Messages ────────────────────

class GroupMessageViewSet(GroupLookupMixin, viewsets.ModelViewSet):
    """
    Chat messages inside a group.

    GET    /api/groups/{finova_id}/messages/       — message history (paginated)
    POST   /api/groups/{finova_id}/messages/       — send a message
    PATCH  /api/groups/{finova_id}/messages/{id}/   — edit or pin/unpin (admin)
    """
    permission_classes = [IsAuthenticated, IsGroupMember]
    http_method_names = ['get', 'post', 'patch']

    def get_queryset(self):
        group = self.get_group()
        return GroupMessage.objects.filter(group=group).select_related('sender')

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupMessageCreateSerializer
        return GroupMessageSerializer

    def perform_create(self, serializer):
        group = self.get_group()
        serializer.save(group=group, sender=self.request.user)

    @action(detail=True, methods=['patch'], url_path='pin')
    def pin(self, request, group_finova_id=None, pk=None):
        """Pin or unpin a message. Admin/moderator only."""
        message = self.get_object()
        group = self.get_group()
        member = group.members.filter(
            user=request.user, role__in=['admin', 'moderator'], is_active=True
        ).first()
        if not member:
            return Response(
                {"error": "Only admins/moderators can pin messages."},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.is_pinned = not message.is_pinned
        message.save(update_fields=['is_pinned'])
        action_word = "pinned" if message.is_pinned else "unpinned"
        return Response({"message": f"Message {action_word}."})


# ──────────────────── Discussions ────────────────────

class DiscussionViewSet(GroupLookupMixin, viewsets.ModelViewSet):
    """
    Discussion-to-Poll Pipeline within a group.

    GET    /api/groups/{finova_id}/discussions/              — list discussions
    POST   /api/groups/{finova_id}/discussions/              — propose a new discussion
    GET    /api/groups/{finova_id}/discussions/{id}/          — discussion detail
    POST   /api/groups/{finova_id}/discussions/{id}/comment/  — add comment
    """
    permission_classes = [IsAuthenticated, IsGroupMember]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        group = self.get_group()
        return Discussion.objects.filter(group=group).select_related('proposed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return DiscussionCreateSerializer
        return DiscussionSerializer

    def perform_create(self, serializer):
        group = self.get_group()
        serializer.save(group=group, proposed_by=self.request.user)

    @action(detail=True, methods=['post'])
    def comment(self, request, group_finova_id=None, pk=None):
        """
        Add a comment to a discussion. Increments engagement.
        Auto-unlocks voting when threshold is met.
        Body: { "content": "I think this is a good buy because..." }
        """
        discussion = self.get_object()

        if discussion.status != 'open':
            return Response(
                {"error": "Discussion is no longer open for comments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = request.data.get('content', '').strip()
        if not content:
            return Response(
                {"error": "Comment content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = DiscussionComment.objects.create(
            discussion=discussion,
            author=request.user,
            content=content,
        )

        # Increment engagement
        discussion.engagement_count += 1
        discussion.save(update_fields=['engagement_count'])

        # Auto-unlock voting if threshold met
        poll = None
        if discussion.can_unlock_voting:
            poll = discussion.unlock_voting()

        response_data = DiscussionCommentSerializer(comment).data
        if poll:
            response_data['voting_unlocked'] = True
            response_data['poll_id'] = str(poll.id)

        return Response(response_data, status=status.HTTP_201_CREATED)


# ──────────────────── Trade Polls & Voting ────────────────────

class TradePollViewSet(GroupLookupMixin, viewsets.ReadOnlyModelViewSet):
    """
    Trade polls and voting within a group.

    GET    /api/groups/{finova_id}/polls/              — list polls
    GET    /api/groups/{finova_id}/polls/{id}/          — poll detail + results
    POST   /api/groups/{finova_id}/polls/{id}/vote/     — cast vote
    """
    permission_classes = [IsAuthenticated, IsGroupMember]
    serializer_class = TradePollSerializer

    def get_queryset(self):
        group = self.get_group()
        return TradePoll.objects.filter(
            discussion__group=group
        ).select_related('discussion')

    @action(detail=True, methods=['post'])
    def vote(self, request, group_finova_id=None, pk=None):
        """
        Cast a vote on a trade poll.
        Body: { "choice": "buy" }  (options: buy, sell, hold)
        """
        poll = self.get_object()

        if poll.status != 'active':
            return Response(
                {"error": "This poll is no longer active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if poll.is_expired:
            poll.resolve()
            return Response(
                {"error": "Voting deadline has passed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check user hasn't already voted
        if Vote.objects.filter(poll=poll, voter=request.user).exists():
            return Response(
                {"error": "You have already voted on this poll."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choice = serializer.validated_data['choice']

        # Create vote
        vote = Vote.objects.create(
            poll=poll, voter=request.user, choice=choice
        )

        # Update tallies
        if choice == 'buy':
            poll.result_buy_count += 1
        elif choice == 'sell':
            poll.result_sell_count += 1
        elif choice == 'hold':
            poll.result_hold_count += 1
        poll.save(update_fields=['result_buy_count', 'result_sell_count', 'result_hold_count'])

        # Increment user's global vote counter
        request.user.record_vote()

        # Check for Turbo-Reduction
        poll.apply_turbo_reduction()

        # Check if quorum met → auto-resolve
        if poll.quorum_met:
            poll.resolve()

        return Response({
            "message": f"Vote '{choice}' recorded.",
            "turbo_applied": poll.turbo_reduction_applied,
            "poll": TradePollSerializer(poll).data,
        }, status=status.HTTP_201_CREATED)
