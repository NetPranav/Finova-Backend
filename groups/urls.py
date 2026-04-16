from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GroupViewSet, GroupMessageViewSet,
    DiscussionViewSet, TradePollViewSet,
)

router = DefaultRouter()
router.register(r'', GroupViewSet, basename='group')

app_name = 'groups'

urlpatterns = [
    # Nested routes under a specific group
    path(
        '<str:group_finova_id>/messages/',
        GroupMessageViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='group-messages',
    ),
    path(
        '<str:group_finova_id>/messages/<uuid:pk>/',
        GroupMessageViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
        name='group-message-detail',
    ),
    path(
        '<str:group_finova_id>/messages/<uuid:pk>/pin/',
        GroupMessageViewSet.as_view({'patch': 'pin'}),
        name='group-message-pin',
    ),
    path(
        '<str:group_finova_id>/discussions/',
        DiscussionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='group-discussions',
    ),
    path(
        '<str:group_finova_id>/discussions/<uuid:pk>/',
        DiscussionViewSet.as_view({'get': 'retrieve'}),
        name='group-discussion-detail',
    ),
    path(
        '<str:group_finova_id>/discussions/<uuid:pk>/comment/',
        DiscussionViewSet.as_view({'post': 'comment'}),
        name='group-discussion-comment',
    ),
    path(
        '<str:group_finova_id>/polls/',
        TradePollViewSet.as_view({'get': 'list'}),
        name='group-polls',
    ),
    path(
        '<str:group_finova_id>/polls/<uuid:pk>/',
        TradePollViewSet.as_view({'get': 'retrieve'}),
        name='group-poll-detail',
    ),
    path(
        '<str:group_finova_id>/polls/<uuid:pk>/vote/',
        TradePollViewSet.as_view({'post': 'vote'}),
        name='group-poll-vote',
    ),
    # Main group CRUD routes (list, create, retrieve, update, delete, join, leave, etc.)
    path('', include(router.urls)),
]
