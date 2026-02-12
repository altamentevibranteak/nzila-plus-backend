from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Carga, Motorista, Veiculo, Cliente


class CargaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carga
        fields = '__all__' # Expõe todos os campos da carga na API

class MotoristaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motorista
        fields = '__all__'

class RegisterSerializer(serializers.ModelSerializer):
    OPCOES_USUARIO = [('motorista', 'Motorista'), 
                      ('cliente', 'Cliente'),
                      ]
    
    telefone = serializers.CharField(write_only=True)
    # Campo adicionais dependo do tipo
    tipo_usuario = serializers.ChoiceField(choices=OPCOES_USUARIO, write_only=True)
    carta_conducao = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'telefone', 'tipo_usuario', 'carta_conducao']

    def create(self, validated_data):
        tipo = validated_data.pop('tipo_usuario')
        telefone = validated_data.pop('telefone')
        carta = validated_data.pop('carta_conducao', None)
        
        # 1. Cria o Usuario base (Auth)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # 2. Logica de decisão
        if tipo == 'motorista':
            Motorista.objects.create(
                user=user,
                telefone=telefone,
                carta_conducao=carta if carta else "PENDENTE")
        else:
            Cliente.objects.create(user=user, telefone=telefone)

        return user    