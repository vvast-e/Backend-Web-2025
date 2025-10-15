from django.urls import path
from . import views

app_name = 'comets'

urlpatterns = [

    path('', views.services_list, name='comets_list'),
    

    path('comet/<int:comet_id>/', views.comet_detail, name='comet_detail'),
    

    path('distance/<int:request_id>/', views.trajectory_calculation_detail, name='trajectory_calculation_detail'),
    

    path('comet/add/<int:comet_id>/', views.add_comet_to_request, name='add_comet_to_request'),
    

    path('distance/<int:request_id>/delete/', views.delete_trajectory_calculation, name='delete_trajectory_calculation'),
]
