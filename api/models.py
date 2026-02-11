from django.db import models
from django.contrib.auth.models import User

# Create your models here.
STATUS_CHOICES = [
    ('pendente', 'Pendente'),
    ('em_transito', 'Em Trânsito'),
    ('entregue', 'Entregue'),
    ('cancelado', 'Cancelado'),
]

class Veiculo(models.Model):
    modelo = models.CharField(max_length=100)
    placa = models.CharField(max_length=20)
    capacidade_kg = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.modelo} ({self.placa})"
    
class Motorista(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    carta_conducao = models.CharField(max_length=50, unique=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    endereço = models.TextField()
    

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Carga(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2)
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    preco_frete = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    # Relacionamentos
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='minhas_cargas')
    motorista = models.ForeignKey(Motorista, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')

    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.status}"
