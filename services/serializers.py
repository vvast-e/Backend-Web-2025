from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Comet, Distance, RequestComet, CustomUser


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


class DistanceSerializer(serializers.ModelSerializer):
    astronomer_login = serializers.EmailField(source='astronomer.email', read_only=True)
    moderator_login = serializers.EmailField(source='moderator.email', read_only=True)
    distance_comets = RequestCometSerializer(many=True, read_only=True)
    
    class Meta:
        model = Distance
        fields = ['id', 'status', 'created_at', 'astronomer_login', 'formed_at', 'completed_at', 
                 'moderator_login', 'astronomers_list', 'telescopes_list', 'total_distance_au', 'distance_comets']
        read_only_fields = ['id', 'created_at', 'formed_at', 'completed_at', 'astronomer_login', 'moderator_login']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']
        extra_kwargs = {
            'is_staff': {'required': False, 'default': False},
            'is_superuser': {'required': False, 'default': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
