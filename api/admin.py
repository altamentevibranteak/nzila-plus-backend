from django.contrib import admin
from .models import Veiculo, Motorista, Cliente, Carga, PushToken


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ['modelo', 'placa', 'capacidade_kg']
    search_fields = ['modelo', 'placa']


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'telefone', 'bi', 'bi_verificado', 'carta_verificado', 'saldo']
    list_filter = ['bi_verificado', 'carta_verificado']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'bi']
    readonly_fields = ['saldo']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'telefone', 'bi', 'endereco']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'bi']


@admin.register(Carga)
class CargaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'cliente', 'motorista', 'status', 'categoria', 'preco_frete', 'distancia_km', 'avaliacao', 'data_criacao']
    list_filter = ['status', 'categoria', 'tipo_servico']
    search_fields = ['titulo', 'origem', 'destino']
    readonly_fields = ['data_criacao', 'preco_frete']


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'atualizado_em']