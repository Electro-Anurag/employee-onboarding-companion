from django.urls import path
from backend.foundation.views import index, health_live, health_ready

urlpatterns = [
    path("", index),
    path("health/live", health_live),
    path("health/ready", health_ready),
]
