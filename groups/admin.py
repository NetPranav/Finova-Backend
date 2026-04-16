from django.contrib import admin
from .models import (
    Group, GroupMember, GroupMessage,
    Discussion, DiscussionComment, TradePoll, Vote,
)


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = [
        'finova_id', 'name', 'risk_level', 'member_count',
        'max_members', 'is_active', 'created_by', 'created_at',
    ]
    list_filter = ['risk_level', 'is_active', 'created_at']
    search_fields = ['finova_id', 'name', 'description']
    readonly_fields = ['id', 'finova_id', 'created_at', 'updated_at']
    inlines = [GroupMemberInline]

    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__finova_id', 'group__name']


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['group', 'sender', 'message_type', 'content_preview', 'is_pinned', 'created_at']
    list_filter = ['message_type', 'is_pinned', 'created_at']
    search_fields = ['content', 'stock_symbol']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = [
        'stock_symbol', 'discussion_type', 'status', 'group',
        'proposed_by', 'engagement_count', 'created_at',
    ]
    list_filter = ['status', 'discussion_type', 'created_at']
    search_fields = ['stock_symbol', 'stock_name']
    readonly_fields = ['id', 'created_at', 'voting_unlocked_at']


@admin.register(DiscussionComment)
class DiscussionCommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'discussion', 'content_preview', 'created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['id', 'created_at']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'


@admin.register(TradePoll)
class TradePollAdmin(admin.ModelAdmin):
    list_display = [
        'discussion', 'status', 'quorum_percentage',
        'result_buy_count', 'result_sell_count', 'result_hold_count',
        'turbo_reduction_applied', 'voting_deadline', 'created_at',
    ]
    list_filter = ['status', 'turbo_reduction_applied']
    readonly_fields = ['id', 'created_at', 'resolved_at']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter', 'poll', 'choice', 'cast_at']
    list_filter = ['choice']
    search_fields = ['voter__username', 'voter__finova_id']
    readonly_fields = ['id', 'cast_at']
