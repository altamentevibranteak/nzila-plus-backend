from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CargaViewSet, MotoristaViewSet

router = DefaultRouter()
router.register(r'cargas', CargaViewSet)
router.register(r'motorista', MotoristaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]