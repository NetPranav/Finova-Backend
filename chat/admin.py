from django.contrib import admin
from .models import Conversation, DirectMessage


class DirectMessageInline(admin.TabularInline):
    model = DirectMessage
    extra = 0
    readonly_fields = ['id', 'sender', 'content', 'message_type', 'stock_symbol', 'is_read', 'created_at']
    fields = ['sender', 'content', 'message_type', 'stock_symbol', 'is_read', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'participant_one_display', 'participant_two_display',
        'message_count', 'is_active', 'created_at', 'updated_at',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = [
        'participant_one__username', 'participant_one__finova_id',
        'participant_two__username', 'participant_two__finova_id',
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [DirectMessageInline]

    def id_short(self, obj):
        return str(obj.id)[:8] + '…'
    id_short.short_description = 'ID'

    def participant_one_display(self, obj):
        return f"{obj.participant_one.username} [{obj.participant_one.finova_id}]"
    participant_one_display.short_description = 'User 1'

    def participant_two_display(self, obj):
        return f"{obj.participant_two.username} [{obj.participant_two.finova_id}]"
    participant_two_display.short_description = 'User 2'

    def message_count(self, obj):
        return obj.direct_messages.count()
    message_count.short_description = 'Messages'


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = [
        'sender_display', 'conversation_display', 'message_type',
        'content_preview', 'is_read', 'created_at',
    ]
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['content', 'stock_symbol', 'sender__username']
    readonly_fields = ['id', 'created_at']

    def sender_display(self, obj):
        return f"{obj.sender.username} [{obj.sender.finova_id}]"
    sender_display.short_description = 'Sender'

    def conversation_display(self, obj):
        return str(obj.conversation.id)[:8] + '…'
    conversation_display.short_description = 'Conv'

    def content_preview(self, obj):
        return obj.content[:80] + '…' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'
