from django.contrib import admin
from .models import Veiculo, Motorista, Cliente, Carga

admin.site.register(Veiculo)
admin.site.register(Motorista)
admin.site.register(Cliente)
admin.site.register(Carga)