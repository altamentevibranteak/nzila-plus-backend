from rest_framework import serializers
from .models import Carga, Motorista, Veiculo

class CargaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carga
        fields = '__all__' # Expõe todos os campos da carga na API

class MotoristaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motorista
        fields = '__all__'