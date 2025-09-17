from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # GET: Список комет с поиском
    path('', views.services_list, name='comets_list'),
    
    # GET: Детали кометы с формой расчёта расстояния
    path('comets/<int:comet_id>/', views.comet_detail, name='comet_detail'),
    
    # GET: Детали заявки на расчёт
    path('requests/<int:request_id>/', views.request_detail, name='request_detail'),
    
    # POST: Добавление кометы в заявку (через ORM)
    path('comets/add/<int:comet_id>/', views.add_comet_to_request, name='add_comet_to_request'),
    
    # POST: Логическое удаление заявки (через SQL UPDATE)
    path('requests/<int:request_id>/delete/', views.delete_request, name='delete_request'),
]

