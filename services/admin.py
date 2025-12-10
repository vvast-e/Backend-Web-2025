from django.contrib import admin
from .models import Comet, Distance, RequestComet


@admin.register(Comet)
class CometAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_deleted']
    list_filter = ['is_deleted']
    search_fields = ['name']


@admin.register(Distance)
class DistanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'astronomer', 'chief_astronomer', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['astronomer__username', 'astronomer__email']


@admin.register(RequestComet)
class RequestCometAdmin(admin.ModelAdmin):
    list_display = ['request', 'comet', 'sort_order', 'distance_au']
    list_filter = ['sort_order']
    search_fields = ['comet__name']