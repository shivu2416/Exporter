from django.urls import path
from .views import *

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)


manual_urlpatterns = [
    path('test/', Test.as_view(), name='test'),
]

urlpatterns = manual_urlpatterns + router.urls