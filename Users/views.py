from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserPublicSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserStatsSerializer
)
from .permissions import IsOwnerOrReadOnly

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    POST /api/users/register/
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            "user": UserProfileSerializer(user, context=self.get_serializer_context()).data,
            "message": "Account created successfully! Please verify your email."
        }, status=status.HTTP_201_CREATED)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user CRUD operations
    
    list: GET /api/users/
    retrieve: GET /api/users/{id}/
    update: PUT /api/users/{id}/
    partial_update: PATCH /api/users/{id}/
    destroy: DELETE /api/users/{id}/
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve' and self.request.user != self.get_object():
            return UserPublicSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserProfileSerializer
    
    def get_queryset(self):
        """
        Optionally filter verified users or search
        """
        queryset = User.objects.all()
        
        # Filter verified users
        verified = self.request.query_params.get('verified', None)
        if verified is not None:
            queryset = queryset.filter(is_verified=True)
        
        # Search by username
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(username__icontains=search)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current authenticated user profile
        GET /api/users/me/
        """
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update current user profile
        PUT/PATCH /api/users/update_profile/
        """
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            "user": UserProfileSerializer(request.user, context={'request': request}).data,
            "message": "Profile updated successfully"
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change user password
        POST /api/users/change_password/
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            "message": "Password changed successfully"
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request, pk=None):
        """
        Get user statistics
        GET /api/users/{id}/stats/
        """
        user = self.get_object()
        serializer = UserStatsSerializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_email(self, request):
        """
        Verify user email (simplified - add token logic later)
        POST /api/users/verify_email/
        """
        # TODO: Implement email verification token logic
        user = request.user
        user.is_verified = True
        user.save()
        
        return Response({
            "message": "Email verified successfully"
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'], permission_classes=[IsAuthenticated])
    def deactivate_account(self, request):
        """
        Deactivate user account (soft delete)
        DELETE /api/users/deactivate_account/
        """
        user = request.user
        user.is_active = False
        user.save()
        
        return Response({
            "message": "Account deactivated successfully"
        }, status=status.HTTP_200_OK)