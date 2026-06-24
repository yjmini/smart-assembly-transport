from django.urls import path
from . import views

urlpatterns = [
    path("api/health", views.health, name="api-health"),
    path("api/orders", views.create_order, name="api-orders"),
    path("api/events", views.record_event, name="api-events"),
    path("api/metrics", views.metrics, name="api-metrics"),
]
