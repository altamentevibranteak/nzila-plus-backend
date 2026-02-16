from django.db import models
from django.contrib.auth.models import User

# Create your models here.
STATUS_CHOICES = [
    ('PENDENTE', 'Pendente'),
    ('EM_TRANSITO', 'Em Trânsito'),
    ('ENTREGUE', 'Entregue'),
    ('CANCELADO', 'Cancelado'),
]

TIPO_SERVICO_CHOICES = [
    ('IMEDIATO', 'Serviço Imediato'),
    ('AGENDADO', 'Serviço Agendado'),
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
    bi = models.CharField(max_length=20, unique=True, verbose_name="Bilhete de Identidade")
    carta_conducao = models.CharField(max_length=50, unique=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=255, blank=True)
    bi = models.CharField(max_length=20, unique=True, verbose_name="Bilhete de Identidade")
    

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Carga(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    peso_kg = models.DecimalField(max_digits=10, decimal_places=2)
    foto_carga = models.ImageField(upload_to='cargas/%Y/%m/%d', null=True, blank=True)
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    origem_coords = models.CharField(max_length=255, blank=True, verbose_name="Coordenadas de Origem (lat,long)")
    destino_coords = models.CharField(max_length=255, blank=True, verbose_name="Coordenadas de Destino (lat,long)")
    preco_frete = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    tipo_servico = models.CharField(
        max_length=20, 
        choices=TIPO_SERVICO_CHOICES, 
        default='IMEDIATO',
        verbose_name="Tipo de Serviço"
    )
    data_agendamento = models.DateTimeField(null=True, blank=True, verbose_name="Data do Agendamento")

    acompanhada = models.BooleanField(
        default=False, 
        verbose_name="Cliente vai acompanhar a carga?"
    )
    
    CATEGORIA_CHOICES = [
        ('construcao', 'Materiais de Construção'),
        ('mobilia', 'Mobiliário/Casa'),
        ('eletro', 'Eletrodomésticos'),
        ('outros', 'Outros/Diversos'),
    ]
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros') 

    # Relacionamentos
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='minhas_cargas')
    motorista = models.ForeignKey(Motorista, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')

    data_criacao = models.DateTimeField(auto_now_add=True)

    def calcular_preco_estimado(self):
        """
        Calcula o preço estimado da carga com base na fórmula:
        Preço Base + (Peso * Taxa de Peso) + (Taxa de Categoria)
        
        Fórmula:
        - Preço Base: 2000 Kz
        - Taxa de Peso: 100 Kz por kg
        - Taxa de Categoria: Construção=1.5x, Mobília=1.2x, Outros=1x
        - Distância: 10km (fixo por enquanto - TODO: Integrar API de Mapas para cálculo dinâmico)
        """
        from decimal import Decimal
        
        # Constantes
        PRECO_BASE = Decimal('2000')  # Kz
        TAXA_PESO = Decimal('100')    # Kz por kg
        DISTANCIA_KM = Decimal('10')  # km (fixo - TODO: Usar Google Maps ou similar para calcular distância real)
        
        # Taxas de categoria
        TAXA_CATEGORIA = {
            'construcao': Decimal('1.5'),
            'mobilia': Decimal('1.2'),
            'eletro': Decimal('1.0'),
            'outros': Decimal('1.0'),
        }
        
        # Cálculo do preço
        taxa_cat = TAXA_CATEGORIA.get(self.categoria, Decimal('1.0'))
        
        # Fórmula: Preço Base + (Peso * Taxa de Peso) com multiplicador da categoria
        preco = PRECO_BASE + (self.peso_kg * TAXA_PESO * taxa_cat)
        
        return preco

    def save(self, *args, **kwargs):
        """
        Sobrescreve o save para calcular automaticamente o preço_frete
        se não estiver definido manualmente.
        """
        # Se o preco_frete não foi definido manualmente, calcula automaticamente
        if self.preco_frete is None:
            self.preco_frete = self.calcular_preco_estimado()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} - {self.status}"
