from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CargaViewSet, MotoristaViewSet, RegisterView
from .views import RegisterView, CustomAuthToken

router = DefaultRouter()
router.register(r'cargas', CargaViewSet)
router.register(r'motorista', MotoristaViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomAuthToken.as_view(), name='auth_login'),
]