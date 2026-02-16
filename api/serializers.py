from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Carga, Motorista, Veiculo, Cliente


class CargaSerializer(serializers.ModelSerializer):
    # Forçamos o campo a ser um ImageField para o Swagger entender
    foto_carga = serializers.ImageField(required=False)

    class Meta:
        model = Carga
        fields = [
            'id', 'titulo', 'descricao', 'peso_kg', 'foto_carga', 
            'origem', 'destino', 'origem_coords', 'destino_coords',
            'preco_frete', 'status', 'tipo_servico', 'data_agendamento',
            'acompanhada', 'categoria', 'cliente', 'motorista',
            'data_criacao'
        ]
        read_only_fields = ['cliente', 'status', 'data_criacao']

class MotoristaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motorista
        fields = '__all__'

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    tipo_usuario = serializers.ChoiceField(choices=[('cliente', 'Cliente'), ('motorista', 'Motorista')], write_only=True)

    bi = serializers.CharField()
    telefone = serializers.CharField(write_only=True)
    morada = serializers.CharField(required=False)
    
    carta_conducao = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'telefone', 'tipo_usuario', 'carta_conducao']

    def create(self, validated_data):
        # 1. Cria o User base (Django Auth)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # 2. Cria o perfil específico com o BI
        tipo = validated_data['tipo_usuario']
        if tipo == 'cliente':
            Cliente.objects.create(
                user=user, 
                bi=validated_data['bi'], 
                telefone=validated_data['telefone'],
                endereco=validated_data.get('morada', '')
            )
        else:
            Motorista.objects.create(
                user=user, 
                bi=validated_data['bi'], 
                telefone=validated_data['telefone']
            )
        
        return user   