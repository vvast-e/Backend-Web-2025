from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Comet, CalculationRequest, RequestComet


class CometSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Comet
        fields = ['id', 'name', 'description', 'price', 'image_key', 'image_url', 'k_x', 'k_y', 'k_z']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        return obj.get_minio_url()


class RequestCometSerializer(serializers.ModelSerializer):
    comet = CometSerializer(read_only=True)
    comet_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = RequestComet
        fields = ['id', 'comet', 'comet_id', 'quantity', 'sort_order', 'is_main', 'coords_x', 'coords_y', 'coords_z']
        read_only_fields = ['id']


class CalculationRequestSerializer(serializers.ModelSerializer):
    astronomer_username = serializers.CharField(source='astronomer.username', read_only=True)
    moderator_username = serializers.CharField(source='moderator.username', read_only=True)
    request_comets = RequestCometSerializer(many=True, read_only=True)
    
    class Meta:
        model = CalculationRequest
        fields = ['id', 'status', 'created_at', 'astronomer_username', 'formed_at', 'completed_at', 
                 'moderator_username', 'astronomers_list', 'telescopes_list', 'total_distance_au', 'request_comets']
        read_only_fields = ['id', 'created_at', 'formed_at', 'completed_at', 'astronomer_username', 'moderator_username']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']
        read_only_fields = ['id', 'is_staff']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user
