from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [

    path('', views.services_list, name='comets_list'),
    

    path('comets/<int:comet_id>/', views.comet_detail, name='comet_detail'),
    

    path('requests/<int:request_id>/', views.request_detail, name='request_detail'),
    

    path('comets/add/<int:comet_id>/', views.add_comet_to_request, name='add_comet_to_request'),
    

    path('requests/<int:request_id>/delete/', views.delete_request, name='delete_request'),
]
