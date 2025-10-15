from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from .authentication import RedisSessionAuthentication
from .permissions import IsManager, IsAdmin
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.models import User
from .models import CustomUser
from django.utils import timezone
from django.conf import settings
import redis
import uuid
import os
import math

# Connect to our Redis instance
session_storage = redis.StrictRedis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT
)

# Fallback хранилище на случай недоступности Redis (в памяти процесса)
_inproc_sessions = {}
from .models import Comet, Distance, RequestComet
from .serializers import CometSerializer, DistanceSerializer, RequestCometSerializer, UserSerializer, LoginSerializer


def get_current_user():
    """Singleton для получения зафиксированного пользователя-создателя"""
    user, created = CustomUser.objects.get_or_create(
        email='admin@comets.com',
        defaults={
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
    return user


def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator


class CometViewSet(viewsets.ModelViewSet):
    queryset = Comet.objects.filter(is_deleted=False)
    serializer_class = CometSerializer
    authentication_classes = [RedisSessionAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post', 'put', 'delete']
    
    def get_queryset(self):
        queryset = Comet.objects.filter(is_deleted=False)
        name = self.request.query_params.get('name', None)
        price_min = self.request.query_params.get('price_min', None)
        price_max = self.request.query_params.get('price_max', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        if price_min:
            queryset = queryset.filter(price__gte=price_min)
        if price_max:
            queryset = queryset.filter(price__lte=price_max)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """Логическое удаление услуги"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(request_body=None)
    @action(detail=True, methods=['post'], url_path='addImage')
    def add_image(self, request, pk=None):
        """Добавление изображения к услуге"""
        comet = self.get_object()
        
        if 'image' not in request.FILES:
            return Response({'error': 'Изображение не предоставлено'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        
        # Генерируем название на латинице
        file_extension = os.path.splitext(image_file.name)[1]
        new_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # Сохраняем в MinIO (здесь упрощенно - в реальности нужна интеграция с MinIO)
        comet.image_key = new_filename
        comet.save()
        
        return Response({'image_key': new_filename}, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(request_body=None)
    @action(detail=True, methods=['post'], url_path='addToRequest')
    def add_to_request(self, request, pk=None):
        """Добавление услуги в заявку-черновик"""
        comet = self.get_object()
        
        # Создаем или получаем заявку-черновик с автозаполнением astronomer
        distance, created = Distance.objects.get_or_create(
            astronomer=request.user,  # АВТОЗАПОЛНЕНИЕ ИЗ request.user
            status='draft',
            defaults={}
        )
        
        # Добавляем услугу в заявку
        request_comet, created = RequestComet.objects.get_or_create(
            request=distance,
            comet=comet,
            defaults={
                'quantity': 1,
                'sort_order': RequestComet.objects.filter(request=distance).count() + 1,
                'is_main': False,
                'coords_x': 0.0,
                'coords_y': 0.0,
                'coords_z': 0.0,
            }
        )
        
        if not created:
            request_comet.quantity += 1
            request_comet.save()
        
        serializer = DistanceSerializer(distance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TrajectoriesViewSet(viewsets.ModelViewSet):
    queryset = Distance.objects.all()
    serializer_class = DistanceSerializer
    authentication_classes = [RedisSessionAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'delete']
    
    def get_queryset(self):
        """Для списка применяем фильтры; для detail-операций возвращаем все заявки."""
        qs = Distance.objects.all()
        if getattr(self, 'action', None) == 'list':
            qs = qs.exclude(status__in=['deleted', 'draft'])
            status_filter = self.request.query_params.get('status', None)
            if status_filter:
                qs = qs.filter(status=status_filter)
            date_from = self.request.query_params.get('date_from', None)
            date_to = self.request.query_params.get('date_to', None)
            if date_from:
                qs = qs.filter(formed_at__gte=date_from)
            if date_to:
                qs = qs.filter(formed_at__lte=date_to)
        return qs

    def retrieve(self, request, pk=None):
        """Получение заявки по id без исключения draft/deleted (по методичке: GET одна запись)."""
        instance = get_object_or_404(Distance, id=pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cart_info(self, request):
        """Получение информации о корзине (заявке-черновике)"""
        try:
            draft_request = Distance.objects.get(
                astronomer=request.user,
                status='draft'
            )
            items_count = RequestComet.objects.filter(request=draft_request).count()
            return Response({
                'request_id': draft_request.id,
                'items_count': items_count
            })
        except Distance.DoesNotExist:
            return Response({
                'request_id': None,
                'items_count': 0
            })
    
    @swagger_auto_schema(request_body=None)
    @action(detail=True, methods=['put'])
    def form_request(self, request, pk=None):
        """Формирование заявки создателем"""
        calc_request = self.get_object()
        
        if calc_request.astronomer != request.user:
            return Response({'error': 'Нет прав для формирования этой заявки'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        if calc_request.status != 'draft':
            return Response({'error': 'Можно формировать только черновики'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверка обязательных полей
        if not calc_request.astronomers_list or not calc_request.telescopes_list:
            return Response({'error': 'Не заполнены обязательные поля'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        calc_request.status = 'formed'
        calc_request.formed_at = timezone.now()
        calc_request.save()
        
        serializer = DistanceSerializer(calc_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'], permission_classes=[IsManager])
    @swagger_auto_schema(request_body=None)
    def complete_request(self, request, pk=None):
        """Завершение/отклонение заявки модератором"""
        calc_request = self.get_object()
        
        if calc_request.status != 'formed':
            return Response({'error': 'Можно завершать только сформированные заявки'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        action_type = request.data.get('action', 'complete')
        moderator = request.user
        
        if action_type == 'complete':
            calc_request.status = 'completed'
            # Расчет общего расстояния
            total_distance = 0
            for req_comet in calc_request.distance_comets.all():
                distance = math.sqrt(
                    (float(req_comet.coords_x) - float(req_comet.comet.k_x))**2 + 
                    (float(req_comet.coords_y) - float(req_comet.comet.k_y))**2 + 
                    (float(req_comet.coords_z) - float(req_comet.comet.k_z))**2
                )
                total_distance += distance * req_comet.quantity
            
            calc_request.total_distance_au = total_distance
        else:
            calc_request.status = 'rejected'
        
        calc_request.moderator = moderator
        calc_request.completed_at = timezone.now()
        calc_request.save()
        
        serializer = DistanceSerializer(calc_request)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Логическое удаление заявки"""
        instance = self.get_object()
        
        if instance.astronomer != request.user:
            return Response({'error': 'Нет прав для удаления этой заявки'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        if instance.status != 'draft':
            return Response({'error': 'Можно удалять только черновики'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        instance.status = 'deleted'
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestCometViewSet(viewsets.ModelViewSet):
    serializer_class = RequestCometSerializer
    authentication_classes = [RedisSessionAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['put', 'delete']
    
    def get_queryset(self):
        request_id = self.kwargs.get('request_id')
        return RequestComet.objects.filter(request_id=request_id)
    
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete_comet_from_request(self, request, request_id=None):
        """Удаление услуги из заявки по comet_id без PK м-м"""
        comet_id = request.data.get('comet_id')
        if not comet_id:
            return Response({'error': 'comet_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            request_comet = RequestComet.objects.get(
                request_id=request_id, 
                comet_id=comet_id
            )
            request_comet.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RequestComet.DoesNotExist:
            return Response({'error': 'Связь не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['put'], url_path='update')
    def update_comet_in_request(self, request, request_id=None):
        """Изменение м-м по comet_id без PK м-м"""
        comet_id = request.data.get('comet_id')
        if not comet_id:
            return Response({'error': 'comet_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            request_comet = RequestComet.objects.get(
                request_id=request_id,
                comet_id=comet_id
            )
            serializer = RequestCometSerializer(
                request_comet, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except RequestComet.DoesNotExist:
            return Response({'error': 'Связь не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    def destroy(self, request, *args, **kwargs):
        """Удаление услуги из заявки (старый метод с PK - оставлен для совместимости)"""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """Создание позиции м-м: привязать request из URL и comet по comet_id."""
        request_id = self.kwargs.get('request_id')
        distance = get_object_or_404(Distance, id=request_id)
        comet_id = serializer.validated_data.pop('comet_id')
        comet = get_object_or_404(Comet, id=comet_id)
        serializer.save(request=distance, comet=comet)

    def update(self, request, *args, **kwargs):
        """Обновление позиции: разрешить передавать comet_id (необязательно)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        comet_id = serializer.validated_data.pop('comet_id', None)
        if comet_id is not None:
            comet = get_object_or_404(Comet, id=comet_id)
            serializer.save(comet=comet)
        else:
            serializer.save()
        return Response(serializer.data)


class UserViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    model_class = CustomUser
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if getattr(self, 'action', None) in ['register']:
            return [AllowAny()]
        return super().get_permissions()

    @swagger_auto_schema(request_body=UserSerializer)
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def register(self, request):
        from .serializers import UserRegistrationSerializer
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'id': user.id, 'email': user.email}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        # поместить текущий session_id в blacklist в Redis
        session_id = request.COOKIES.get('session_id')
        try:
            if session_id:
                r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                # отмечаем как отозванный с коротким TTL, чтобы не копить мусор
                r.setex(f"bl:{session_id}", 60 * 60 * 24, '1')
        except Exception:
            pass
        logout(request)
        return Response({'message': 'Успешный выход'})

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([AllowAny])
@authentication_classes([])
@csrf_exempt
@swagger_auto_schema(method='post', request_body=LoginSerializer)
@api_view(['POST'])
def login_view(request):
    # Принимаем и JSON (request.data), и form-data/x-www-form-urlencoded (request.POST)
    email = (getattr(request, 'data', {}) or {}).get('email') or request.POST.get('email')
    password = (getattr(request, 'data', {}) or {}).get('password') or request.POST.get('password')

    if not email or not password:
        return Response({'status': 'error', 'error': 'email/password required'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)
    if user is not None:
        random_key = str(uuid.uuid4())
        try:
            session_storage.set(random_key, email)
        except Exception:
            return Response({'status': 'error', 'error': 'redis unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response = Response({'status': 'ok'})
        response.set_cookie('session_id', random_key)
        return response
    return Response({'status': 'error', 'error': 'login failed'}, status=status.HTTP_401_UNAUTHORIZED)


def logout_view(request):
    # ручной logout из корневого роута
    session_id = request.COOKIES.get('session_id')
    try:
        if session_id:
            r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            r.setex(f"bl:{session_id}", 60 * 60 * 24, '1')
    except Exception:
        pass
    logout(request._request)
    return Response({'status': 'Success'})
