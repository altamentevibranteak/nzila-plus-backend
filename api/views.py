from django.shortcuts import render
from rest_framework import viewsets
from .models import Carga, Motorista
from .serializers import CargaSerializer, MotoristaSerializer

# Create your views here.
class CargaViewSet(viewsets.ModelViewSet):
    queryset = Carga.objects.all()
    serializer_class = CargaSerializer

class MotoristaViewSet(viewsets.ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer