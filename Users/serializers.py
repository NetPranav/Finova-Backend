from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import date

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'date_of_birth', 'gender_identity',
            'gender_identity_custom', 'bio'
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        
        # Validate age (must be 18+)
        if attrs.get('date_of_birth'):
            today = date.today()
            age = today.year - attrs['date_of_birth'].year - (
                (today.month, today.day) < 
                (attrs['date_of_birth'].month, attrs['date_of_birth'].day)
            )
            if age < 18:
                raise serializers.ValidationError({
                    "date_of_birth": "You must be at least 18 years old to register."
                })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full user profile serializer (private data included)
    """
    age = serializers.ReadOnlyField()
    display_gender = serializers.ReadOnlyField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'date_of_birth', 'age', 'gender_identity',
            'gender_identity_custom', 'display_gender', 'profile_picture',
            'bio', 'is_verified', 'phone_number', 'consensus_score',
            'learning_level', 'user_level', 'total_reels_watched', 'total_votes_cast',
            'notification_preferences', 'privacy_settings',
            'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'email', 'is_verified', 'consensus_score',
            'total_reels_watched', 'total_votes_cast', 'created_at',
            'updated_at', 'last_login'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Public-facing user profile (limited data)
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'profile_picture',
            'bio', 'consensus_score', 'learning_level', 'user_level',
            'is_verified', 'created_at'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile
    """
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'date_of_birth',
            'gender_identity', 'gender_identity_custom', 'profile_picture',
            'bio', 'phone_number', 'notification_preferences',
            'privacy_settings'
        ]
    
    def validate_username(self, value):
        """Ensure username is unique (excluding current user)"""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserStatsSerializer(serializers.ModelSerializer):
    """
    User statistics and gamification data
    """
    class Meta:
        model = User
        fields = [
            'consensus_score', 'learning_level', 'user_level', 'total_reels_watched',
            'total_votes_cast'
        ]