from rest_framework import permissions


class IsGroupMember(permissions.BasePermission):
    """
    Only active group members can access group content.
    Expects the view to have a `get_group()` method or `group` attribute.
    """
    message = "You must be a member of this group."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        group = view.get_group()
        if group is None:
            return False
        return group.members.filter(
            user=request.user, is_active=True
        ).exists()


class IsGroupAdmin(permissions.BasePermission):
    """
    Only group admins can perform admin actions (edit settings, manage members).
    """
    message = "Only group admins can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        group = view.get_group()
        if group is None:
            return False
        return group.members.filter(
            user=request.user, role='admin', is_active=True
        ).exists()


class IsGroupAdminOrModerator(permissions.BasePermission):
    """
    Group admins or moderators can perform moderation actions.
    """
    message = "Only group admins or moderators can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        group = view.get_group()
        if group is None:
            return False
        return group.members.filter(
            user=request.user,
            role__in=['admin', 'moderator'],
            is_active=True
        ).exists()
