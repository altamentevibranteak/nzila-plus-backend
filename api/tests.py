from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from .models import Cliente, Motorista, Veiculo, Carga


# ─────────────────────────────────────────────
# Helpers reutilizáveis
# ─────────────────────────────────────────────

def criar_cliente(username='cliente1', password='pass1234'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    cliente = Cliente.objects.create(user=user, telefone='900000001', bi=f'BI{username}')
    token = Token.objects.create(user=user)
    return user, cliente, token

def criar_motorista(username='motorista1', password='pass1234', docs_verificados=True):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    veiculo = Veiculo.objects.create(modelo='Toyota Hilux', placa=f'LD-{username[:4]}-AA', capacidade_kg=1000, cor='Branco')
    motorista = Motorista.objects.create(
        user=user, telefone='900000002', bi=f'BIM{username}',
        carta_conducao=f'CARTA{username}', veiculo=veiculo,
        bi_verificado=docs_verificados,
        carta_verificado=docs_verificados,
        livrete_verificado=docs_verificados,
    )
    token = Token.objects.create(user=user)
    return user, motorista, token

def criar_carga(cliente, origem_coords='-8.8383,13.2344'):
    return Carga.objects.create(
        titulo='Teste de Carga', descricao='Carga de teste',
        peso_kg=100, origem='Luanda', destino='Viana',
        origem_coords=origem_coords, destino_coords='-8.9035,13.3047',
        distancia_km=15, categoria='outros', cliente=cliente, status='PENDENTE',
    )


# ─────────────────────────────────────────────
# 1. AUTENTICAÇÃO
# ─────────────────────────────────────────────

class AutenticacaoTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_registo_cliente(self):
        res = self.client.post('/api/register/', {
            'username': 'novo_cliente', 'password': 'pass1234',
            'email': 'cliente@test.com', 'tipo_usuario': 'cliente',
            'bi': 'BI999', 'telefone': '900111222',
        })
        self.assertEqual(res.status_code, 201)
        print('✅ Registo de cliente')

    def test_registo_motorista(self):
        res = self.client.post('/api/register/', {
            'username': 'novo_motorista', 'password': 'pass1234',
            'email': 'motorista@test.com', 'tipo_usuario': 'motorista',
            'bi': 'BI888', 'telefone': '900333444', 'carta_conducao': 'CARTA999',
        })
        self.assertEqual(res.status_code, 201)
        print('✅ Registo de motorista')

    def test_login_devolve_token_e_tipo(self):
        criar_cliente(username='login_test')
        res = self.client.post('/api/login/', {'username': 'login_test', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        self.assertEqual(res.data['user_type'], 'cliente')
        print('✅ Login devolve token e tipo de utilizador')

    def test_login_password_errada(self):
        criar_cliente(username='login_errado')
        res = self.client.post('/api/login/', {'username': 'login_errado', 'password': 'errada'})
        self.assertEqual(res.status_code, 400)
        print('✅ Login com password errada rejeitado')

    def test_logout_apaga_token(self):
        _, _, token = criar_cliente(username='logout_test')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        res = self.client.post('/api/logout/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        print('✅ Logout apaga token correctamente')

    def test_acesso_sem_token_negado(self):
        res = self.client.get('/api/perfil/cliente/')
        self.assertEqual(res.status_code, 401)
        print('✅ Acesso sem token negado')


# ─────────────────────────────────────────────
# 2. CARGAS
# ─────────────────────────────────────────────

class CargaTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user_c, self.cliente, self.token_c = criar_cliente()
        self.user_m, self.motorista, self.token_m = criar_motorista()

    def test_cliente_cria_carga(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post('/api/cargas/', {
            'titulo': 'Mudança sala', 'descricao': 'Sofá e mesa',
            'peso_kg': '80', 'origem': 'Maianga', 'destino': 'Rangel',
            'origem_coords': '-8.8383,13.2344', 'destino_coords': '-8.9035,13.3047',
            'distancia_km': '10', 'categoria': 'mobilia',
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'PENDENTE')
        self.assertIsNotNone(res.data['preco_frete'])
        print('✅ Cliente cria carga — preço calculado automaticamente')

    def test_motorista_nao_pode_criar_carga(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.post('/api/cargas/', {
            'titulo': 'Indevida', 'descricao': 'Teste',
            'peso_kg': '50', 'origem': 'A', 'destino': 'B', 'categoria': 'outros',
        })
        self.assertEqual(res.status_code, 400)
        print('✅ Motorista bloqueado de criar carga')

    def test_cargas_disponiveis_com_localizacao(self):
        criar_carga(self.cliente, origem_coords='-8.8383,13.2344')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.get('/api/cargas/disponiveis/?lat=-8.8400&lon=13.2350&raio=5')
        self.assertEqual(res.status_code, 200)
        self.assertIn('cargas', res.data)
        self.assertGreater(res.data['total'], 0)
        self.assertIn('distancia_ate_origem', res.data['cargas'][0])
        print('✅ Filtro por raio com Haversine funciona')

    def test_motorista_sem_docs_nao_aceita(self):
        _, _, token_sem_docs = criar_motorista(username='sem_docs', docs_verificados=False)
        carga = criar_carga(self.cliente)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token_sem_docs.key}')
        res = self.client.post(f'/api/cargas/{carga.id}/aceitar/')
        self.assertEqual(res.status_code, 403)
        self.assertIn('documentos_pendentes', res.data)
        print('✅ Motorista sem documentos verificados bloqueado')

    def test_ciclo_completo_carga(self):
        # 1. Criar carga
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post('/api/cargas/', {
            'titulo': 'Ciclo completo', 'descricao': 'Teste de fluxo',
            'peso_kg': '50', 'origem': 'Luanda', 'destino': 'Viana',
            'origem_coords': '-8.8383,13.2344', 'destino_coords': '-8.9035,13.3047',
            'distancia_km': '12', 'categoria': 'outros',
        })
        self.assertEqual(res.status_code, 201)
        carga_id = res.data['id']
        preco = float(res.data['preco_frete'])
        print(f'  → Carga criada (id={carga_id}, preço={preco} Kz)')

        # 2. Motorista aceita
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.post(f'/api/cargas/{carga_id}/aceitar/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['veiculo']['cor'], 'Branco')
        print(f'  → Motorista aceitou (veículo: {res.data["veiculo"]["cor"]})')

        # 3. Finalizar entrega
        res = self.client.post(f'/api/cargas/{carga_id}/finalizar-entrega/')
        self.assertEqual(res.status_code, 200)
        print('  → Entrega finalizada')

        # 4. Saldo creditado
        self.motorista.refresh_from_db()
        self.assertEqual(float(self.motorista.saldo), preco)
        print(f'  → Saldo creditado: {self.motorista.saldo} Kz')

        # 5. Avaliar
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post(f'/api/cargas/{carga_id}/avaliar/', {'avaliacao': 5})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['avaliacao'], 5)
        print('✅ Ciclo completo passou!')

    def test_cliente_cancela_carga_pendente(self):
        carga = criar_carga(self.cliente)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post(f'/api/cargas/{carga.id}/cancelar/')
        self.assertEqual(res.status_code, 200)
        carga.refresh_from_db()
        self.assertEqual(carga.status, 'CANCELADO')
        print('✅ Cliente cancela carga PENDENTE')

    def test_cliente_nao_cancela_em_transito(self):
        carga = criar_carga(self.cliente)
        carga.status = 'EM_TRANSITO'
        carga.motorista = self.motorista
        carga.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post(f'/api/cargas/{carga.id}/cancelar/')
        self.assertEqual(res.status_code, 400)
        print('✅ Cancelamento de carga EM_TRANSITO bloqueado')

    def test_avaliacao_dupla_bloqueada(self):
        carga = criar_carga(self.cliente)
        carga.status = 'ENTREGUE'
        carga.motorista = self.motorista
        carga.avaliacao = 4
        carga.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.post(f'/api/cargas/{carga.id}/avaliar/', {'avaliacao': 5})
        self.assertEqual(res.status_code, 400)
        print('✅ Avaliação dupla bloqueada')

    def test_motorista_so_uma_viagem_activa(self):
        carga1 = criar_carga(self.cliente)
        carga1.status = 'EM_TRANSITO'
        carga1.motorista = self.motorista
        carga1.save()
        carga2 = criar_carga(self.cliente)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.post(f'/api/cargas/{carga2.id}/aceitar/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('viagem_activa_id', res.data)
        print('✅ Motorista bloqueado de aceitar 2 viagens simultâneas')


# ─────────────────────────────────────────────
# 3. PERFIS
# ─────────────────────────────────────────────

class PerfilTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user_c, self.cliente, self.token_c = criar_cliente()
        self.user_m, self.motorista, self.token_m = criar_motorista()

    def test_ver_perfil_cliente(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.get('/api/perfil/cliente/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['username'], 'cliente1')
        print('✅ Perfil do cliente visível')

    def test_ver_perfil_motorista(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.get('/api/perfil/motorista/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('saldo', res.data)
        self.assertIn('avaliacao_media', res.data)
        self.assertEqual(res.data['veiculo']['cor'], 'Branco')
        print('✅ Perfil do motorista visível (saldo + avaliação + veículo)')

    def test_editar_perfil_cliente(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.patch('/api/perfil/cliente/editar/', {
            'telefone': '911222333', 'first_name': 'André',
        })
        self.assertEqual(res.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.telefone, '911222333')
        print('✅ Edição de perfil do cliente')

    def test_mudar_password_gera_novo_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_c.key}')
        res = self.client.patch('/api/perfil/cliente/editar/', {'password': 'novapass9999'})
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data.get('novo_token'))
        self.assertFalse(Token.objects.filter(key=self.token_c.key).exists())
        print('✅ Mudança de password gera novo token')

    def test_carteira_motorista(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_m.key}')
        res = self.client.get('/api/perfil/motorista/carteira/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('saldo', res.data)
        self.assertIn('historico', res.data)
        self.assertEqual(float(res.data['saldo']), 0.0)
        print('✅ Carteira do motorista (saldo inicial 0 Kz)')


# ─────────────────────────────────────────────
# 4. CÁLCULO DE PREÇO
# ─────────────────────────────────────────────

class CalculoPrecoTestCase(TestCase):

    def setUp(self):
        _, self.cliente, _ = criar_cliente()

    def test_preco_construcao(self):
        carga = Carga.objects.create(
            titulo='Teste', descricao='Teste', peso_kg=100,
            origem='A', destino='B', distancia_km=20,
            categoria='construcao', cliente=self.cliente, status='PENDENTE',
        )
        # 2000 + (100 * 100 * 1.5) + (20 * 50) = 18000
        self.assertEqual(float(carga.preco_frete), 18000.0)
        print(f'✅ Preço construção: {carga.preco_frete} Kz')

    def test_preco_mobilia(self):
        carga = Carga.objects.create(
            titulo='Teste', descricao='Teste', peso_kg=50,
            origem='A', destino='B', distancia_km=10,
            categoria='mobilia', cliente=self.cliente, status='PENDENTE',
        )
        # 2000 + (50 * 100 * 1.2) + (10 * 50) = 8500
        self.assertEqual(float(carga.preco_frete), 8500.0)
        print(f'✅ Preço mobília: {carga.preco_frete} Kz')

    def test_preco_fallback_sem_distancia(self):
        carga = Carga.objects.create(
            titulo='Teste', descricao='Teste', peso_kg=100,
            origem='A', destino='B', categoria='outros',
            cliente=self.cliente, status='PENDENTE',
        )
        # 2000 + (100 * 100 * 1.0) + (10 * 50) = 12500
        self.assertEqual(float(carga.preco_frete), 12500.0)
        print(f'✅ Fallback 10km: {carga.preco_frete} Kz')