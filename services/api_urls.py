from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CometViewSet, TrajectoriesViewSet, RequestCometViewSet, UserViewSet
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes

router = DefaultRouter()
router.register(r'comets', CometViewSet, basename='comet')
router.register(r'distance', TrajectoriesViewSet, basename='distance')

urlpatterns = [
    path('', include(router.urls)),
    # M2M только кастомные методы без PK
    path('distance/<int:request_id>/comets/delete/',
         RequestCometViewSet.as_view({'delete': 'delete_comet_from_request'})),
    path('distance/<int:request_id>/comets/update/',
         RequestCometViewSet.as_view({'put': 'update_comet_in_request'})),
    path('distance/<int:request_id>/comets/<int:comet_id>/',
         RequestCometViewSet.as_view({'put': 'update_comet_by_id'}), name='update-comet-by-id'),

    # Пользовательские действия без auto CRUD
    path('users/register/', UserViewSet.as_view({'post': 'register'})),
    path('users/login/', UserViewSet.as_view({'post': 'login'})),
    path('users/profile/', UserViewSet.as_view({'get': 'profile', 'put': 'update_profile'})),
    path('users/logout/', UserViewSet.as_view({'post': 'logout'})),
]
