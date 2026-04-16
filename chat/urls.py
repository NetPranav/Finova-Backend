from django.urls import path
from .views import (
    StartConversationView, FindUserView,
    ConversationListView, ConversationMessageListView,
    MarkReadView,
)

app_name = 'chat'

urlpatterns = [
    # Start a new conversation by Finova ID
    path('start/', StartConversationView.as_view(), name='start-conversation'),

    # Find / lookup a user by their Finova ID
    path('find/<str:finova_id>/', FindUserView.as_view(), name='find-user'),

    # List all conversations
    path('', ConversationListView.as_view(), name='conversation-list'),

    # Messages within a conversation
    path(
        '<uuid:conversation_id>/messages/',
        ConversationMessageListView.as_view(),
        name='conversation-messages',
    ),

    # Mark all messages in a conversation as read
    path(
        '<uuid:conversation_id>/read/',
        MarkReadView.as_view(),
        name='mark-read',
    ),
]
