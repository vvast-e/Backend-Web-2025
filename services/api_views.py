from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os
import math
from .models import Comet, CalculationRequest, RequestComet
from .serializers import CometSerializer, CalculationRequestSerializer, RequestCometSerializer, UserSerializer


def get_current_user():
    """Singleton для получения зафиксированного пользователя-создателя"""
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@comets.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
    return user


class CometViewSet(viewsets.ModelViewSet):
    queryset = Comet.objects.filter(is_deleted=False)
    serializer_class = CometSerializer
    permission_classes = [AllowAny]
    
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
    
    @action(detail=True, methods=['post'], url_path='addToRequest')
    def add_to_request(self, request, pk=None):
        """Добавление услуги в заявку-черновик"""
        comet = self.get_object()
        current_user = get_current_user()
        
        # Создаем или получаем заявку-черновик
        calc_request, created = CalculationRequest.objects.get_or_create(
            astronomer=current_user,
            status='draft',
            defaults={}
        )
        
        # Добавляем услугу в заявку
        request_comet, created = RequestComet.objects.get_or_create(
            request=calc_request,
            comet=comet,
            defaults={
                'quantity': 1,
                'sort_order': RequestComet.objects.filter(request=calc_request).count() + 1,
                'is_main': False,
                'coords_x': 0.0,
                'coords_y': 0.0,
                'coords_z': 0.0,
            }
        )
        
        if not created:
            request_comet.quantity += 1
            request_comet.save()
        
        serializer = CalculationRequestSerializer(calc_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TrajectoriesViewSet(viewsets.ModelViewSet):
    queryset = CalculationRequest.objects.all()
    serializer_class = CalculationRequestSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options']
    
    def get_queryset(self):
        """Для списка применяем фильтры; для detail-операций возвращаем все заявки."""
        qs = CalculationRequest.objects.all()
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
        instance = get_object_or_404(CalculationRequest, id=pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cart_info(self, request):
        """Получение информации о корзине (заявке-черновике)"""
        current_user = get_current_user()
        
        try:
            draft_request = CalculationRequest.objects.get(
                astronomer=current_user,
                status='draft'
            )
            items_count = RequestComet.objects.filter(request=draft_request).count()
            return Response({
                'request_id': draft_request.id,
                'items_count': items_count
            })
        except CalculationRequest.DoesNotExist:
            return Response({
                'request_id': None,
                'items_count': 0
            })
    
    @action(detail=True, methods=['put'])
    def form_request(self, request, pk=None):
        """Формирование заявки создателем"""
        calc_request = self.get_object()
        current_user = get_current_user()
        
        if calc_request.astronomer != current_user:
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
        
        serializer = CalculationRequestSerializer(calc_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'])
    def complete_request(self, request, pk=None):
        """Завершение/отклонение заявки модератором"""
        calc_request = self.get_object()
        
        if calc_request.status != 'formed':
            return Response({'error': 'Можно завершать только сформированные заявки'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        action_type = request.data.get('action', 'complete')
        moderator = get_current_user()
        
        if action_type == 'complete':
            calc_request.status = 'completed'
            # Расчет общего расстояния
            total_distance = 0
            for req_comet in calc_request.request_comets.all():
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
        
        serializer = CalculationRequestSerializer(calc_request)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Логическое удаление заявки"""
        instance = self.get_object()
        current_user = get_current_user()
        
        if instance.astronomer != current_user:
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
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        request_id = self.kwargs.get('request_id')
        return RequestComet.objects.filter(request_id=request_id)
    
    def destroy(self, request, *args, **kwargs):
        """Удаление услуги из заявки"""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """Создание позиции м-м: привязать request из URL и comet по comet_id."""
        request_id = self.kwargs.get('request_id')
        calc_request = get_object_or_404(CalculationRequest, id=request_id)
        comet_id = serializer.validated_data.pop('comet_id')
        comet = get_object_or_404(Comet, id=comet_id)
        serializer.save(request=calc_request, comet=comet)

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


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Регистрация нового пользователя"""
        from .serializers import UserRegistrationSerializer
        
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'id': user.id, 'username': user.username}, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Получение профиля текущего пользователя"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Аутентификация пользователя"""
        from django.contrib.auth import authenticate
        
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            from django.contrib.auth import login
            login(request, user)
            return Response({'message': 'Успешная аутентификация'})
        return Response({'error': 'Неверные учетные данные'}, 
                      status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Деавторизация пользователя"""
        from django.contrib.auth import logout
        logout(request)
        return Response({'message': 'Успешный выход'})
