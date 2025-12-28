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
from django.utils import timezone
from django.conf import settings
import redis
import uuid
import os
import math
import requests

# Connect to our Redis instance
session_storage = redis.StrictRedis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT
)

# Fallback хранилище на случай недоступности Redis (в памяти процесса)
_inproc_sessions = {}
from .models import Comet, Distance, RequestComet
from .serializers import CometSerializer, DistanceSerializer, RequestCometSerializer, UserSerializer, LoginSerializer


def get_current_user(request):
    """Получение текущего пользователя из запроса"""
    return request.user


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
    @action(detail=True, methods=['post'], url_path='addToRequest', permission_classes=[IsAuthenticated])
    def add_to_request(self, request, pk=None):
        """Добавление услуги в заявку-черновик"""
        # Используем текущего пользователя из запроса
        current_user = get_current_user(request)
        
        comet = self.get_object()
        
        distance, created = Distance.objects.get_or_create(
            astronomer=current_user,
            status='draft',
            defaults={}
        )
        
        # Добавляем услугу в заявку
        request_comet, created = RequestComet.objects.get_or_create(
            request=distance,
            comet=comet,
            defaults={
                'sort_order': RequestComet.objects.filter(request=distance).count() + 1,
                'coords_x': 0.0,
                'coords_y': 0.0,
                'coords_z': 0.0,
            }
        )
        
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
            print(f"[GET_QUERYSET] Action: list, User: {self.request.user.username} (ID: {self.request.user.id}, is_superuser: {self.request.user.is_superuser})")
            
            # Для обычных пользователей показываем только их заявки, для модераторов - все
            if not self.request.user.is_superuser:
                qs = qs.filter(astronomer=self.request.user)
                print(f"[GET_QUERYSET] Filtered by astronomer: {self.request.user.id}")
            
            # Исключаем черновики и удаленные
            qs = qs.exclude(status__in=['deleted', 'draft'])
            print(f"[GET_QUERYSET] After exclude draft/deleted, count: {qs.count()}")
            
            status_filter = self.request.query_params.get('status', None)
            if status_filter:
                qs = qs.filter(status=status_filter)
                print(f"[GET_QUERYSET] Filtered by status: {status_filter}")
            date_from = self.request.query_params.get('date_from', None)
            date_to = self.request.query_params.get('date_to', None)
            if date_from:
                qs = qs.filter(formed_at__gte=date_from)
                print(f"[GET_QUERYSET] Filtered by date_from: {date_from}")
            if date_to:
                qs = qs.filter(formed_at__lte=date_to)
                print(f"[GET_QUERYSET] Filtered by date_to: {date_to}")
            
            # Логируем количество заявок и их детали
            requests_list = list(qs.values('id', 'status', 'astronomer_id', 'astronomer__username', 'formed_at'))
            print(f"[GET_QUERYSET] Found {len(requests_list)} requests after filters: {requests_list}")
            
            # Логируем все заявки в БД для данного пользователя (для отладки)
            all_user_requests = list(Distance.objects.filter(astronomer=self.request.user).values('id', 'status', 'astronomer_id', 'formed_at'))
            print(f"[GET_QUERYSET] All requests in DB for user {self.request.user.id}: {all_user_requests}")
        return qs

    def list(self, request, *args, **kwargs):
        """Переопределяем list для логирования ответа"""
        response = super().list(request, *args, **kwargs)
        print(f"[LIST] Response data type: {type(response.data)}, length: {len(response.data) if isinstance(response.data, list) else 'not a list'}")
        print(f"[LIST] Response data: {response.data}")
        return response

    def retrieve(self, request, pk=None):
        """Получение заявки по id без исключения draft/deleted (по методичке: GET одна запись)."""
        instance = get_object_or_404(Distance, id=pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cart_info(self, request):
        """Получение информации о корзине (заявке-черновике)"""
        # Используем текущего пользователя из запроса
        current_user = get_current_user(request)
        try:
            draft_request = Distance.objects.get(
                astronomer=current_user,
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
        print(f"[FORM_REQUEST] Starting form request for ID: {pk}, Current status: {calc_request.status}, Astronomer ID: {calc_request.astronomer.id}")
        
        # Используем текущего пользователя из запроса
        current_user = get_current_user(request)
        print(f"[FORM_REQUEST] Current user from get_current_user(): {current_user.username} (ID: {current_user.id})")
        print(f"[FORM_REQUEST] Request user: {request.user.username} (ID: {request.user.id})")
        
        if calc_request.astronomer != current_user:
            print(f"[FORM_REQUEST] Permission denied: astronomer {calc_request.astronomer.id} != current_user {current_user.id}")
            return Response({'error': 'Нет прав для формирования этой заявки'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        if calc_request.status != 'draft':
            print(f"[FORM_REQUEST] Invalid status: {calc_request.status}, expected 'draft'")
            return Response({'error': 'Можно формировать только черновики'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверка обязательных полей
        if not calc_request.telescopes_list:
            print(f"[FORM_REQUEST] telescopes_list is empty")
            return Response({'error': 'Не заполнены обязательные поля'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        calc_request.status = 'formed'
        calc_request.formed_at = timezone.now()
        calc_request.save()
        print(f"[FORM_REQUEST] Request {pk} successfully formed. New status: {calc_request.status}, formed_at: {calc_request.formed_at}, Astronomer ID: {calc_request.astronomer.id}")
        print(f"[FORM_REQUEST] Request astronomer username: {calc_request.astronomer.username}")
        
        serializer = DistanceSerializer(calc_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'], permission_classes=[IsAdmin], url_path='complete')
    @swagger_auto_schema(request_body=None)
    def complete_request(self, request, pk=None):
        """Завершение/отклонение заявки главным астрономом"""
        calc_request = self.get_object()
        
        if calc_request.status != 'formed':
            return Response({'error': 'Можно завершать только сформированные заявки'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        action_type = request.data.get('action', 'complete')
        chief_astronomer = request.user
        
        if action_type == 'complete':
            try:
                for req_comet in calc_request.distance_comets.all():
                    print(f"Calling async service for request {calc_request.id}, comet {req_comet.id}")
                    async_response = requests.post(
                        'http://localhost:8081/process',
                        json={
                            'request_id': calc_request.id,
                            'comet_id': req_comet.id,
                            'coords_x': float(req_comet.coords_x),
                            'coords_y': float(req_comet.coords_y),
                            'coords_z': float(req_comet.coords_z),
                            'k_x': float(req_comet.comet.k_x),
                            'k_y': float(req_comet.comet.k_y),
                            'k_z': float(req_comet.comet.k_z),
                        },
                        timeout=5
                    )
                    print(f"Async service response: status={async_response.status_code}, body={async_response.text}")
                    if async_response.status_code == 202:
                        print(f"Successfully sent request {calc_request.id}, comet {req_comet.id} to async service")
            except Exception as e:
                print(f"Error calling async service: {e}")
                import traceback
                traceback.print_exc()
        
        calc_request.chief_astronomer = chief_astronomer
        calc_request.completed_at = timezone.now()
        calc_request.save()
        
        serializer = DistanceSerializer(calc_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'], permission_classes=[], url_path='async-result')
    @swagger_auto_schema(request_body=None)
    def async_result(self, request, pk=None):
        """Приём результата асинхронного сервиса с псевдоавторизацией по токену"""
        ASYNC_TOKEN = '8bytekey'
        
        token = request.headers.get('X-Async-Token')
        if token != ASYNC_TOKEN:
            return Response({'error': 'Неверный токен'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        calc_request = self.get_object()
        
        if calc_request.status != 'formed':
            return Response({'error': 'Можно обновлять только сформированные заявки'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        comet_id = request.data.get('comet_id')
        if not comet_id:
            return Response({'error': 'comet_id is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            req_comet = RequestComet.objects.get(request=calc_request, id=comet_id)
        except RequestComet.DoesNotExist:
            return Response({'error': 'Comet not found in request'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        result_status = request.data.get('status')
        if result_status == 'completed':
            distance_au = request.data.get('distance_au')
            if distance_au is not None:
                req_comet.distance_au = distance_au
                req_comet.save()
        elif result_status == 'rejected':
            req_comet.distance_au = None
            req_comet.save()
        
        all_calculated = calc_request.distance_comets.filter(distance_au__isnull=False).count()
        total_comets = calc_request.distance_comets.count()
        
        if all_calculated == total_comets and total_comets > 0:
            calc_request.status = 'completed'
            calc_request.save()
        elif result_status == 'rejected':
            calc_request.status = 'rejected'
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


class RequestCometViewSet(viewsets.ViewSet):
    """
    Обработка операций над м-м связью заявки и услуги.
    По требованию остаются только два метода без указания PK м-м:
    DELETE и PUT с передачей comet_id.
    """
    authentication_classes = [RedisSessionAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_request_comet(self, request_id, comet_id):
        return RequestComet.objects.get(
            request_id=request_id,
            comet_id=comet_id
        )

    @action(detail=False, methods=['delete'], url_path='delete')
    def delete_comet_from_request(self, request, request_id=None):
        """Удаление услуги из заявки по comet_id без PK м-м"""
        comet_id = request.data.get('comet_id')
        if not comet_id:
            return Response({'error': 'comet_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            request_comet = self._get_request_comet(request_id, comet_id)
            request_comet.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RequestComet.DoesNotExist:
            return Response({'error': 'Связь не найдена'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['put'], url_path='update')
    def update_comet_in_request(self, request, **kwargs):
        """Изменение количества/порядка/координат по comet_id без PK м-м (deprecated)"""
        request_id = kwargs.get('request_id')
        comet_id = request.data.get('comet_id')
        if not comet_id:
            return Response({'error': 'comet_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            request_comet = self._get_request_comet(request_id, comet_id)
        except RequestComet.DoesNotExist:
            return Response({'error': 'Связь не найдена'}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {'sort_order', 'coords_x', 'coords_y', 'coords_z'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = RequestCometSerializer(request_comet, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update_comet_by_id(self, request, **kwargs):
        """Обновление м-м записи по request_id и comet_id"""
        if hasattr(request, 'resolver_match') and request.resolver_match:
            request_id = request.resolver_match.kwargs.get('request_id')
            comet_id = request.resolver_match.kwargs.get('comet_id')
        else:
            request_id = kwargs.get('request_id')
            comet_id = kwargs.get('comet_id')
        
        if not request_id or not comet_id:
            return Response({'error': f'request_id и comet_id обязательны. Получено: request_id={request_id}, comet_id={comet_id}'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            request_id = int(request_id)
            comet_id = int(comet_id)
        except (ValueError, TypeError):
            return Response({'error': 'request_id и comet_id должны быть числами'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            request_comet = self._get_request_comet(request_id, comet_id)
        except RequestComet.DoesNotExist:
            all_request_comets = RequestComet.objects.filter(request_id=request_id).values_list('comet_id', flat=True)
            return Response({
                'error': f'Связь не найдена: request_id={request_id}, comet_id={comet_id}',
                'available_comets': list(all_request_comets)
            }, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {'sort_order', 'coords_x', 'coords_y', 'coords_z'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = RequestCometSerializer(request_comet, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ViewSet):
    authentication_classes = [RedisSessionAuthentication, SessionAuthentication, BasicAuthentication]
    model_class = User
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if getattr(self, 'action', None) in ['register', 'login']:
            return [AllowAny()]
        return super().get_permissions()

    @swagger_auto_schema(request_body=UserSerializer)
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def register(self, request):
        from .serializers import UserRegistrationSerializer
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_email = user.email or user.username
            return Response({'id': user.id, 'email': user_email}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """
        Возвращает профиль текущего пользователя.
        Для анонимного пользователя явно отдаем 401 вместо попытки сериализовать AnonymousUser.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {'detail': 'Необходимо выполнить вход'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = UserSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        session_id = request.COOKIES.get('session_id')
        try:
            if session_id:
                # Используем глобальный session_storage вместо создания нового экземпляра
                session_storage.setex(f"bl:{session_id}", 60 * 60 * 24, '1')
                session_storage.delete(session_id)
        except Exception:
            pass
        logout(request)
        response = Response({'message': 'Успешный выход'})
        response.delete_cookie('session_id')
        return response

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(method='post', request_body=LoginSerializer)
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def login(self, request):
        """Аутентификация с установкой session_id cookie"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Ищем пользователя по email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'status': 'error', 'error': 'login failed'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Проверяем пароль
        if not user.check_password(password):
            return Response({'status': 'error', 'error': 'login failed'}, status=status.HTTP_401_UNAUTHORIZED)

        random_key = str(uuid.uuid4())
        try:
            # Устанавливаем TTL 24 часа для сессии
            session_storage.setex(random_key, 3600 * 24, email)
        except Exception:
            return Response({'status': 'error', 'error': 'redis unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        user_email = user.email or user.username
        response = Response({'status': 'ok', 'user': {'email': user_email, 'id': user.id, 'is_superuser': user.is_superuser}})
        response.set_cookie('session_id', random_key, httponly=True)
        return response

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Деавторизация через ViewSet (заменяет старый logout_view)"""
        session_id = request.COOKIES.get('session_id')
        try:
            if session_id:
                # Используем глобальный session_storage вместо создания нового экземпляра
                session_storage.setex(f"bl:{session_id}", 60 * 60 * 24, '1')
                session_storage.delete(session_id)
        except Exception:
            pass
        logout(request)
        response = Response({'message': 'Успешный выход'})
        response.delete_cookie('session_id')
        return response
