from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CometViewSet, CalculationRequestViewSet, RequestCometViewSet, UserViewSet

router = DefaultRouter()
router.register(r'comets', CometViewSet, basename='comet')
router.register(r'requests', CalculationRequestViewSet, basename='request')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('requests/<int:request_id>/comets/', RequestCometViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('requests/<int:request_id>/comets/<int:pk>/', RequestCometViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
]
