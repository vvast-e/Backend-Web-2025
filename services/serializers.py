from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from .models import Comet, Distance, RequestComet


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
        fields = ['id', 'comet', 'comet_id', 'sort_order', 'coords_x', 'coords_y', 'coords_z', 'distance_au']
        read_only_fields = ['id']


class DistanceSerializer(serializers.ModelSerializer):
    astronomer_login = serializers.SerializerMethodField()
    chief_astronomer_login = serializers.SerializerMethodField()
    distance_comets = RequestCometSerializer(many=True, read_only=True)
    calculated_comets_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Distance
        fields = ['id', 'status', 'created_at', 'astronomer_login', 'formed_at', 'completed_at', 
                 'chief_astronomer_login', 'telescopes_list', 'calculated_comets_count', 'distance_comets']
        read_only_fields = ['id', 'created_at', 'formed_at', 'completed_at', 'astronomer_login', 'chief_astronomer_login']
    
    def get_calculated_comets_count(self, obj):
        return obj.calculated_comets_count()
    
    def get_astronomer_login(self, obj):
        if obj.astronomer:
            return obj.astronomer.email or obj.astronomer.username
        return None
    
    def get_chief_astronomer_login(self, obj):
        if obj.chief_astronomer:
            return obj.chief_astronomer.email or obj.chief_astronomer.username
        return None


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(required=False)
    is_superuser = serializers.BooleanField(default=False, required=False, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_superuser']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.pop('email', None)
        if email:
            instance.email = email
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'username': {'required': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        username = validated_data.pop('username', email)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        attrs['username'] = email
        return attrs
