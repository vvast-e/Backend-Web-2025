from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.services_list, name='list'),

    path('<int:service_id>/', views.service_detail, name='detail'),

    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
]

