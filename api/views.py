from django.shortcuts import render
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from .models import Carga, Motorista
from .serializers import CargaSerializer, MotoristaSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response


# Create your views here.
class CargaViewSet(viewsets.ModelViewSet):
    queryset = Carga.objects.all()
    serializer_class = CargaSerializer

class MotoristaViewSet(viewsets.ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,) # Qualquer pessoa pode se registar!
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "username": serializer.data.get('username'),
                "message": "Usuário e Motorista criados com sucesso!",
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token,  created = Token.objects.get_or_create(user=user)

        # Lógica para identificar o tipo de usuário
        user_type = "desconhecido"
        if hasattr(user, 'motorista'):
            user_type = "motorista"
        elif hasattr(user, 'clinte'):
            user_type = "cliente"
        elif user.is_superuser:
            user_type = "admin"

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'user_type': user_type
        })       