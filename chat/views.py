from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Conversation, DirectMessage
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    DirectMessageSerializer, DirectMessageCreateSerializer,
    StartConversationSerializer,
)

User = get_user_model()


# ──────────────────── Start Conversation ────────────────────

class StartConversationView(APIView):
    """
    POST /api/chat/start/
    Start a new 1:1 conversation by providing the other user's Finova ID.
    If a conversation already exists, return it instead.
    Body: { "finova_id": "THT919" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        target_finova_id = serializer.validated_data['finova_id']
        target_user = User.objects.get(finova_id=target_finova_id)

        # Check if conversation already exists (in either direction)
        existing = Conversation.objects.filter(
            Q(participant_one=request.user, participant_two=target_user)
            | Q(participant_one=target_user, participant_two=request.user)
        ).first()

        if existing:
            return Response({
                "message": "Conversation already exists.",
                "conversation_id": str(existing.id),
                "is_new": False,
            }, status=status.HTTP_200_OK)

        # Create new conversation (lower ID as participant_one for consistency)
        conversation = Conversation.objects.create(
            participant_one=request.user,
            participant_two=target_user,
        )

        return Response({
            "message": f"Conversation started with {target_user.username}.",
            "conversation_id": str(conversation.id),
            "other_user_finova_id": target_user.finova_id,
            "other_user_username": target_user.username,
            "is_new": True,
        }, status=status.HTTP_201_CREATED)


# ──────────────────── Find User ────────────────────

class FindUserView(APIView):
    """
    GET /api/chat/find/<finova_id>/
    Look up a user by their Finova ID before starting a chat.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, finova_id):
        finova_id = finova_id.upper().strip()
        user = get_object_or_404(User, finova_id=finova_id)

        return Response({
            "finova_id": user.finova_id,
            "username": user.username,
            "profile_picture": (
                request.build_absolute_uri(user.profile_picture.url)
                if user.profile_picture else None
            ),
            "user_level": user.user_level,
            "bio": user.bio,
            "is_verified": user.is_verified,
        })


# ──────────────────── Conversation List ────────────────────

class ConversationListView(generics.ListAPIView):
    """
    GET /api/chat/
    List all conversations for the authenticated user, ordered by most recent activity.
    Each item shows the other participant, last message preview, and unread count.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(participant_one=user) | Q(participant_two=user),
            is_active=True,
        ).select_related(
            'participant_one', 'participant_two'
        ).prefetch_related(
            'direct_messages'
        ).order_by('-updated_at')


# ──────────────────── Messages in a Conversation ────────────────────

class ConversationMessageListView(generics.ListCreateAPIView):
    """
    GET  /api/chat/<conversation_id>/messages/   — paginated message history
    POST /api/chat/<conversation_id>/messages/   — send a new message
    """
    permission_classes = [IsAuthenticated]

    def get_conversation(self):
        conversation_id = self.kwargs['conversation_id']
        user = self.request.user
        return get_object_or_404(
            Conversation,
            id=conversation_id,
            is_active=True,
        )

    def get_queryset(self):
        conversation = self.get_conversation()
        # Verify the requesting user is a participant
        user = self.request.user
        if user != conversation.participant_one and user != conversation.participant_two:
            return DirectMessage.objects.none()
        return DirectMessage.objects.filter(
            conversation=conversation
        ).select_related('sender').order_by('created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DirectMessageCreateSerializer
        return DirectMessageSerializer

    def perform_create(self, serializer):
        conversation = self.get_conversation()
        user = self.request.user
        # Verify sender is a participant
        if user != conversation.participant_one and user != conversation.participant_two:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not a participant in this conversation.")
        serializer.save(conversation=conversation, sender=user)
        # Update conversation's updated_at to bubble it up in the list
        conversation.save(update_fields=['updated_at'])


# ──────────────────── Mark as Read ────────────────────

class MarkReadView(APIView):
    """
    POST /api/chat/<conversation_id>/read/
    Mark all unread messages in this conversation as read (for the requesting user).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation, id=conversation_id, is_active=True
        )
        user = request.user
        if user != conversation.participant_one and user != conversation.participant_two:
            return Response(
                {"error": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Mark all messages from the OTHER user as read
        updated_count = DirectMessage.objects.filter(
            conversation=conversation,
            is_read=False,
        ).exclude(sender=user).update(is_read=True)

        return Response({
            "message": f"{updated_count} messages marked as read.",
            "updated_count": updated_count,
        })
