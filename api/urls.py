from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CargaViewSet, EditarPerfilClienteView, MotoristaViewSet,
    RegisterView, CustomAuthToken, PerfilClienteView, PerfilMotoristaView,
    RegistarPushTokenView, EditarPerfilMotoristaView, CarteiraMotoristaView,
    LogoutView
)

router = DefaultRouter()
router.register(r'cargas', CargaViewSet)
router.register(r'motorista', MotoristaViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomAuthToken.as_view(), name='auth_login'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('perfil/cliente/', PerfilClienteView.as_view(), name='perfil_cliente'),
    path('perfil/motorista/', PerfilMotoristaView.as_view(), name='perfil_motorista'),
    path('perfil/motorista/carteira/', CarteiraMotoristaView.as_view(), name='carteira_motorista'),
    path('notificacoes/registar-token/', RegistarPushTokenView.as_view(), name='registar_push_token'),
    path('perfil/motorista/editar/', EditarPerfilMotoristaView.as_view()),
    path('perfil/cliente/editar/', EditarPerfilClienteView.as_view()),
]