from django.contrib.auth import Group, User
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model= User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', ]
        
        
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model= Group
        fields = ['url', 'name']