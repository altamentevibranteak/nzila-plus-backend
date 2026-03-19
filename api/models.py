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
    cor = models.CharField(max_length=50, blank=True, verbose_name="Cor do veículo")

    foto_placa = models.ImageField(upload_to='veiculos/placas/', blank=True, null=True)
    foto_veiculo = models.ImageField(upload_to='veiculos/fotos/', blank=True, null=True)

    def __str__(self):
        return f"{self.modelo} ({self.placa}) — {self.cor}"
    
class Motorista(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    bi = models.CharField(max_length=20, unique=True, verbose_name="Bilhete de Identidade")
    carta_conducao = models.CharField(max_length=50, unique=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.SET_NULL, null=True, blank=True)

    # ✅ NOVOS campos de documentos
    foto_bi_frente = models.ImageField(upload_to='documentos/bi/frente/', blank=True, null=True)
    foto_bi_verso = models.ImageField(upload_to='documentos/bi/verso/', blank=True, null=True)
    foto_carta_frente = models.ImageField(upload_to='documentos/carta/frente/', blank=True, null=True)
    foto_carta_verso = models.ImageField(upload_to='documentos/carta/verso/', blank=True, null=True)
    foto_livrete = models.ImageField(upload_to='documentos/livretes/', blank=True, null=True)
    bi_verificado = models.BooleanField(default=False)
    carta_verificado = models.BooleanField(default=False)
    livrete_verificado = models.BooleanField(default=False)
    
    foto_perfil = models.ImageField(upload_to='perfis/motoristas/', blank=True, null=True)

    # Carteira digital — saldo acumulado de entregas
    saldo = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Saldo da carteira (Kz)"
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=255, blank=True)
    bi = models.CharField(max_length=20, unique=True, verbose_name="Bilhete de Identidade")
    
    foto_perfil = models.ImageField(upload_to='perfis/clientes/', blank=True, null=True)

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

    distancia_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Distância em km (calculada pelo frontend)"
    )

    # Relacionamentos
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='minhas_cargas')
    motorista = models.ForeignKey(Motorista, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas')

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_entrega = models.DateTimeField(null=True, blank=True, verbose_name="Data de Entrega")

    # Avaliação do cliente ao motorista (1 a 5 estrelas)
    avaliacao = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name="Avaliação do motorista (1-5 estrelas)"
    )

    motoristas_recusaram = models.ManyToManyField(
        'Motorista',
        blank=True,
        related_name='cargas_recusadas'
    )

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
        PRECO_BASE = Decimal('2000')      # Kz
        TAXA_PESO = Decimal('100')        # Kz por kg
        TAXA_DISTANCIA = Decimal('50')   # Kz por km

        # Usa a distância real enviada pelo frontend (Mapbox), ou 10km como fallback
        distancia = self.distancia_km if self.distancia_km else Decimal('10')

        # Taxas de categoria
        TAXA_CATEGORIA = {
            'construcao': Decimal('1.5'),
            'mobilia': Decimal('1.2'),
            'eletro': Decimal('1.0'),
            'outros': Decimal('1.0'),
        }

        taxa_cat = TAXA_CATEGORIA.get(self.categoria, Decimal('1.0'))

        # Fórmula: Preço Base + (Peso × Taxa Peso × Categoria) + (Distância × Taxa Distância)
        preco = PRECO_BASE + (self.peso_kg * TAXA_PESO * taxa_cat) + (distancia * TAXA_DISTANCIA)

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
    

class PushToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='push_token')
    token = models.CharField(max_length=255)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.token[:20]}..."