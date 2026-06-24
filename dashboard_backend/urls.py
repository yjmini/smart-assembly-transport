from django.urls import include, path
from dashboard_backend.operations import views

urlpatterns = [
    path("assets/<path:path>", views.dashboard_asset, name="dashboard-asset"),
    path("map/<path:path>", views.dashboard_map_asset, name="dashboard-map-asset"),
    path("", views.dashboard_index, name="dashboard-index"),
    path("", include("dashboard_backend.operations.urls")),
]
