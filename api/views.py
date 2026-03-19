from urllib import request
from django.shortcuts import render
from django.db.models import Avg, F
from rest_framework import viewsets, generics, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Carga, Motorista
from .serializers import CargaSerializer, MotoristaSerializer, RegisterSerializer
from django.contrib.auth.models import User
from math import radians, sin, cos, sqrt, atan2

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, extend_schema_view


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """
    Fórmula de Haversine — calcula a distância em km entre dois pontos GPS.
    Não precisa de API externa, funciona directamente no backend.
    """
    R = 6371  # Raio da Terra em km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# Create your views here.
class EmptySerializer(serializers.Serializer):
    pass

@extend_schema_view(
    create=extend_schema(summary="Criar carga com imagem"),
    update=extend_schema(summary="Atualizar carga com imagem"),
)

class CargaViewSet(viewsets.ModelViewSet):
    queryset = Carga.objects.all()
    serializer_class = CargaSerializer
    parser_classes = (MultiPartParser, FormParser) # Essencial para upload de fotos

    def get_queryset(self):
        """
        Filtra as cargas com base no tipo de utilizador:
        - Cliente: vê apenas suas próprias cargas
        - Motorista: 
          - Para aceitar/disponiveis: vê cargas PENDENTE sem motorista atribuído
          - Caso contrário: vê cargas atribuídas a ele, excluindo as PENDENTES
        - Admin: vê todas as cargas
        
        Ordena sempre pelas mais recentes.
        """
        user = self.request.user
        queryset = Carga.objects.all().order_by('-data_criacao')
        
        # Se for um Cliente
        if hasattr(user, 'cliente'):
            queryset = queryset.filter(cliente=user.cliente)
        
        # Se for um Motorista
        elif hasattr(user, 'motorista'):
            # Actions para aceitar cargas: mostrar PENDENTE sem motorista
            if self.action in ['aceitar', 'disponiveis', 'recusar']:
                queryset = queryset.filter(status='PENDENTE', motorista__isnull=True)
            else:
                # Cargas atribuídas ao motorista (excetuando PENDENTE)
                queryset = queryset.filter(
                    motorista=user.motorista
                ).exclude(status='PENDENTE')
        
        # Se for Admin, vê tudo (já está filtrado por all())
        
        return queryset

    def perform_create(self, serializer):
        # Verifica se o utilizador tem o atributo cliente (se é um Cliente)
        if hasattr(self.request.user, 'cliente'):
            # Associa automaticamente o cliente e define o status como PENDENTE
            serializer.save(cliente=self.request.user.cliente, status='PENDENTE')
        else:
            # Se for um Motorista ou Admin a tentar criar carga, dá um erro amigável
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Apenas utilizadores do tipo Cliente podem criar cargas.")

    @action(detail=False, methods=['get'], url_path='disponiveis')
    def disponiveis(self, request):
        """
        Lista cargas disponíveis para o motorista.
        
        Parâmetros opcionais na query string:
          - lat: latitude actual do motorista (ex: -8.8383)
          - lon: longitude actual do motorista (ex: 13.2344)
          - raio: distância máxima em km da origem da carga (default: 15km)
        
        Se lat/lon forem enviados:
          - Filtra apenas cargas dentro do raio
          - Ordena da mais próxima para a mais distante
          - Devolve o campo distancia_ate_origem em cada carga
        
        Se lat/lon não forem enviados:
          - Comportamento anterior — devolve todas as cargas PENDENTE
        """
        if not hasattr(request.user, 'motorista') and not request.user.is_staff:
            return Response({"erro": "Apenas motoristas podem aceder."}, status=403)

        cargas = Carga.objects.filter(
            status='PENDENTE',
            motorista__isnull=True
        ).exclude(
            motoristas_recusaram=request.user.motorista
        )

        # Tenta ler a localização do motorista da query string
        try:
            lat_motorista = float(request.query_params.get('lat'))
            lon_motorista = float(request.query_params.get('lon'))
            raio_km = float(request.query_params.get('raio', 15))
            tem_localizacao = True
        except (TypeError, ValueError):
            tem_localizacao = False

        if tem_localizacao:
            # Calcula distância para cada carga e filtra pelo raio
            cargas_com_distancia = []

            for carga in cargas:
                # Origem da carga tem de ter coordenadas preenchidas
                if not carga.origem_coords:
                    continue
                try:
                    lat_carga, lon_carga = map(float, carga.origem_coords.split(','))
                except (ValueError, AttributeError):
                    continue

                dist = calcular_distancia_km(
                    lat_motorista, lon_motorista,
                    lat_carga, lon_carga
                )

                if dist <= raio_km:
                    cargas_com_distancia.append((carga, round(dist, 2)))

            # Ordena da mais próxima para a mais distante
            cargas_com_distancia.sort(key=lambda x: x[1])

            # Serializa e adiciona distancia_ate_origem a cada item
            resultado = []
            for carga, dist in cargas_com_distancia:
                dados = CargaSerializer(carga).data
                dados['distancia_ate_origem'] = dist
                resultado.append(dados)

            return Response({
                "total": len(resultado),
                "raio_km": raio_km,
                "cargas": resultado
            })

        # Sem localização — devolve tudo ordenado por data
        cargas = cargas.order_by('-data_criacao')
        serializer = self.get_serializer(cargas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='aceitar', url_name='aceitar', serializer_class=EmptySerializer)
    def aceitar(self, request, pk=None):
        # 1. Busca a carga
        carga = self.get_object()
        
        # 2. Verifica se o user é motorista
        if not hasattr(request.user, 'motorista'):
            return Response({"erro": "Apenas motoristas podem aceitar cargas."}, status=403)
        
        motorista_logado = request.user.motorista

        # Verifica se os documentos foram todos verificados pelo admin
        docs_em_falta = []
        if not motorista_logado.bi_verificado:
            docs_em_falta.append("BI")
        if not motorista_logado.carta_verificado:
            docs_em_falta.append("Carta de Condução")
        if not motorista_logado.livrete_verificado:
            docs_em_falta.append("Livrete")

        if docs_em_falta:
            return Response({
                "erro": "Os teus documentos ainda não foram verificados pelo administrador.",
                "documentos_pendentes": docs_em_falta
            }, status=403)

        # Bloquear se motorista já tem viagem activa
        viagem_activa = Carga.objects.filter(
            motorista=motorista_logado, 
            status='EM_TRANSITO'
        ).first()

        if viagem_activa:
            return Response({
                "erro": f"Já tens uma viagem em curso: \"{viagem_activa.titulo}\". Finaliza-a antes de aceitar outra.",
                "viagem_activa_id": viagem_activa.id
            }, status=400)

        # 3. VALIDAÇÃO: Se a carga já tem motorista ou não está PENDENTE
        if carga.motorista is not None:
            return Response({
                "erro": "Esta carga já foi aceita por outro motorista.",
                "motorista": str(carga.motorista)
            }, status=400)

        if carga.status != 'PENDENTE':
            return Response({"erro": "Carga não disponível."}, status=400)

        # 4. AGORA SIM, GRAVA:
        try:
            carga.status = 'EM_TRANSITO'
            carga.motorista = motorista_logado
            carga.save()
            notificar_atualizacao_carga(carga)
            # Notifica o cliente que a carga foi aceite
            enviar_notificacao(
                carga.cliente.user,
                '🚛 Carga aceite!',
                f'A tua carga "{carga.titulo}" foi aceite por um motorista.'
            )
            
            # Em vez de: serializer = self.get_serializer(carga)
            # Usa o serializer principal para a resposta:
            serializer = CargaSerializer(carga)
            return Response({
                "mensagem": "Carga aceita com sucesso!",
                "carga": serializer.data,
                "veiculo": {
                    "modelo": motorista_logado.veiculo.modelo if motorista_logado.veiculo else None,
                    "cor": motorista_logado.veiculo.cor if motorista_logado.veiculo else None,
                    "placa": motorista_logado.veiculo.placa if motorista_logado.veiculo else None,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"erro": f"Erro ao salvar: {str(e)}"}, status=400)

    @action(detail=True, methods=['post'], url_path='cancelar', url_name='cancelar', serializer_class=EmptySerializer)
    def cancelar(self, request, pk=None):
        """
        Cliente cancela a sua própria carga.
        Só é possível cancelar cargas com status PENDENTE.
        Endpoint: POST /api/cargas/{id}/cancelar/
        """
        if not hasattr(request.user, 'cliente'):
            return Response({"erro": "Apenas clientes podem cancelar cargas."}, status=403)

        carga = self.get_object()

        if carga.cliente != request.user.cliente:
            return Response({"erro": "Não podes cancelar uma carga que não é tua."}, status=403)

        if carga.status != 'PENDENTE':
            return Response({
                "erro": f"Só é possível cancelar cargas PENDENTES. Status actual: {carga.status}"
            }, status=400)

        carga.status = 'CANCELADO'
        carga.save()

        return Response({
            "mensagem": "Carga cancelada com sucesso.",
            "carga_id": carga.id
        }, status=200)

    @action(detail=True, methods=['post'], url_path='recusar', url_name='recusar', serializer_class=EmptySerializer)
    def recusar(self, request, pk=None):
        if not hasattr(request.user, 'motorista'):
            return Response({"erro": "Apenas motoristas podem recusar cargas."}, status=403)

        try:
            carga = self.get_object()
        except:
            return Response({"erro": "Carga não encontrada."}, status=404)

        if carga.status != 'PENDENTE':
            return Response({"erro": f"Esta carga não pode ser recusada. Status: {carga.status}"}, status=400)

        # ✅ NOVO: Guardar quem recusou para não mostrar novamente
        carga.motoristas_recusaram.add(request.user.motorista)
        carga.save()

        return Response({
            "mensagem": "Carga recusada com sucesso!",
            "carga_id": carga.id
        }, status=200)

    @action(detail=True, methods=['post'], url_path='finalizar-entrega', url_name='finalizar_entrega', serializer_class=EmptySerializer)
    def finalizar_entrega(self, request, pk=None):
        """
        Motorista marca uma carga como entregue.
        Apenas o motorista atribuído à carga pode finalizá-la.
        Endpoint: POST /api/cargas/{id}/finalizar-entrega/
        
        Requer: URL com o ID da carga
        Sem campos adicionais no corpo da requisição.
        """
        try:
            # 1. Verificar se o usuário é motorista
            if not hasattr(request.user, 'motorista'):
                return Response(
                    {"erro": "Apenas motoristas podem finalizar entregas."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            motorista_logado = request.user.motorista
            carga = self.get_object()
            
        except Carga.DoesNotExist:
            return Response(
                {"erro": "Carga não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"erro": f"Erro ao buscar carga: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Verificar se o motorista logado é o assignado à carga
        if carga.motorista != motorista_logado:
            return Response(
                {
                    "erro": "Apenas o motorista atribuído pode finalizar esta carga.",
                    "motorista_atribuido": str(carga.motorista)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 3. Verificar se a carga está em EM_TRANSITO
        if carga.status != 'EM_TRANSITO':
            return Response(
                {
                    "erro": f"Carga não pode ser finalizada. Status atual: {carga.status}",
                    "status_atual": carga.status
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. Alterar status para ENTREGUE e salvar
        try:
            from django.utils import timezone
            carga.status = 'ENTREGUE'
            carga.data_entrega = timezone.now()
            carga.save()

            # Credita o valor do frete na carteira do motorista
            if carga.preco_frete:
                Motorista.objects.filter(pk=motorista_logado.pk).update(
                    saldo=F('saldo') + carga.preco_frete
                )

            notificar_atualizacao_carga(carga)
            enviar_notificacao(
                carga.cliente.user,
                '✅ Carga entregue!',
                f'A tua carga "{carga.titulo}" foi entregue com sucesso!'
            )

            serializer = CargaSerializer(carga)
            return Response(
                {
                    "mensagem": "Carga entregue com sucesso!",
                    "carga": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"erro": f"Erro ao finalizar entrega: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='avaliar', url_name='avaliar')
    def avaliar(self, request, pk=None):
        """
        Cliente avalia o motorista após entrega (1 a 5 estrelas).
        Endpoint: POST /api/cargas/{id}/avaliar/
        Body: { "avaliacao": 5 }
        """
        if not hasattr(request.user, 'cliente'):
            return Response({"erro": "Apenas clientes podem avaliar."}, status=403)

        carga = self.get_object()

        if carga.cliente != request.user.cliente:
            return Response({"erro": "Não podes avaliar uma carga que não é tua."}, status=403)

        if carga.status != 'ENTREGUE':
            return Response({"erro": "Só podes avaliar após a entrega."}, status=400)

        if carga.avaliacao is not None:
            return Response({"erro": "Esta entrega já foi avaliada."}, status=400)

        nota = request.data.get('avaliacao')
        if nota is None or not str(nota).isdigit() or not (1 <= int(nota) <= 5):
            return Response({"erro": "A avaliação deve ser um número entre 1 e 5."}, status=400)

        carga.avaliacao = int(nota)
        carga.save()

        return Response({
            "mensagem": "Avaliação registada com sucesso!",
            "avaliacao": carga.avaliacao
        }, status=200)


class MotoristaViewSet(viewsets.ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer


class CarteiraMotoristaView(APIView):
    """
    Devolve o saldo da carteira e o histórico de entregas pagas.
    Endpoint: GET /api/perfil/motorista/carteira/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'motorista'):
            return Response({"erro": "Utilizador não é motorista."}, status=403)

        motorista = request.user.motorista
        # Recarrega para garantir saldo actualizado
        motorista.refresh_from_db()

        entregas_pagas = motorista.entregas.filter(
            status='ENTREGUE'
        ).values('id', 'titulo', 'preco_frete', 'data_entrega', 'avaliacao').order_by('-data_entrega')

        return Response({
            "saldo": motorista.saldo,
            "total_entregas": motorista.entregas.filter(status='ENTREGUE').count(),
            "historico": list(entregas_pagas)
        })


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,) # Qualquer pessoa pode se registar!
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # O método create já grava o User e o Cliente/Motorista
            user = serializer.save() 
            
            # Aqui está o truque: não usamos serializer.data porque ele tenta ler o tipo_usuario
            return Response({
                "message": "Usuário criado com sucesso!",
                "username": user.username,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
    
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token,  created = Token.objects.get_or_create(user=user)

        # Lógica para identificar o tipo de usuário
        user_type = "desconhecido"
        if hasattr(user, 'motorista'):
            user_type = "motorista"
        elif hasattr(user, 'cliente'):
            user_type = "cliente"
        elif user.is_superuser:
            user_type = "admin"

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'user_type': user_type
        })       

class PerfilClienteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'cliente'):
            return Response({"erro": "Utilizador não é cliente."}, status=403)
        
        cliente = user.cliente
        return Response({
            "id": cliente.id,
            "username": user.username,
            "email": user.email,
            "nome_completo": user.get_full_name(),
            "telefone": cliente.telefone,
            "bi": cliente.bi,
            "endereco": cliente.endereco,
            "foto_perfil": request.build_absolute_uri(cliente.foto_perfil.url) if cliente.foto_perfil else None,
            "total_cargas": cliente.minhas_cargas.count(),
            "cargas_pendentes": cliente.minhas_cargas.filter(status='PENDENTE').count(),
            "cargas_em_transito": cliente.minhas_cargas.filter(status='EM_TRANSITO').count(),
            "cargas_entregues": cliente.minhas_cargas.filter(status='ENTREGUE').count(),
        })

class PerfilMotoristaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'motorista'):
            return Response({"erro": "Utilizador não é motorista."}, status=403)
        
        motorista = user.motorista
        veiculo = motorista.veiculo

        return Response({
            "id": motorista.id,
            "username": user.username,
            "email": user.email,
            "nome_completo": user.get_full_name(),
            "telefone": motorista.telefone,
            "bi": motorista.bi,
            "carta_conducao": motorista.carta_conducao,

            # ✅ NOVOS campos de documentos
            "foto_bi_frente": request.build_absolute_uri(motorista.foto_bi_frente.url) if motorista.foto_bi_frente else None,
            "foto_bi_verso": request.build_absolute_uri(motorista.foto_bi_verso.url) if motorista.foto_bi_verso else None,
            "foto_carta_frente": request.build_absolute_uri(motorista.foto_carta_frente.url) if motorista.foto_carta_frente else None,
            "foto_carta_verso": request.build_absolute_uri(motorista.foto_carta_verso.url) if motorista.foto_carta_verso else None,
            "foto_livrete": request.build_absolute_uri(motorista.foto_livrete.url) if motorista.foto_livrete else None,
            "bi_verificado": motorista.bi_verificado,
            "carta_verificado": motorista.carta_verificado,
            "livrete_verificado": motorista.livrete_verificado,

            "foto_perfil": request.build_absolute_uri(motorista.foto_perfil.url) if motorista.foto_perfil else None,

            "veiculo": {
                "modelo": veiculo.modelo,
                "placa": veiculo.placa,
                "cor": veiculo.cor,
                "capacidade_kg": str(veiculo.capacidade_kg),
                "foto_placa": request.build_absolute_uri(veiculo.foto_placa.url) if veiculo.foto_placa else None,
                "foto_veiculo": request.build_absolute_uri(veiculo.foto_veiculo.url) if veiculo.foto_veiculo else None,
            } if veiculo else None,

            "total_entregas": motorista.entregas.count(),
            "entregas_em_transito": motorista.entregas.filter(status='EM_TRANSITO').count(),
            "entregas_concluidas": motorista.entregas.filter(status='ENTREGUE').count(),

            # Carteira digital
            "saldo": motorista.saldo,

            # Média de avaliações (ignora entregas sem avaliação)
            "avaliacao_media": motorista.entregas.filter(
                avaliacao__isnull=False
            ).aggregate(media=Avg('avaliacao'))['media'],
        })

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notificar_atualizacao_carga(carga):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'cargas',
        {
            'type': 'carga_update',
            'data': {
                'id': carga.id,
                'status': carga.status,
                'titulo': carga.titulo,
            }
        }
    )

from .models import PushToken

class RegistarPushTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('push_token')
        if not token:
            return Response({'erro': 'Token não fornecido.'}, status=400)
        
        PushToken.objects.update_or_create(
            user=request.user,
            defaults={'token': token}
        )
        return Response({'mensagem': 'Token registado com sucesso!'})
    
import httpx

def enviar_notificacao(user, titulo, mensagem):
    try:
        push_token = user.push_token.token
        httpx.post('https://exp.host/--/api/v2/push/send', json={
            'to': push_token,
            'title': titulo,
            'body': mensagem,
            'sound': 'default',
        })
    except Exception as e:
        print(f'Erro ao enviar notificação: {e}')    

class EditarPerfilMotoristaView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'motorista'):
            return Response({"erro": "Não é motorista."}, status=403)

        motorista = user.motorista

        # Dados do utilizador Django
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
            user.save()
            # Apaga o token actual — força novo login com a nova password
            Token.objects.filter(user=user).delete()
            novo_token = Token.objects.create(user=user)
            token_actualizado = novo_token.key
        else:
            user.save()
            token_actualizado = None
        if 'telefone' in request.data:
            motorista.telefone = request.data['telefone']
        if 'bi' in request.data:
            motorista.bi = request.data['bi']
        if 'carta_conducao' in request.data:
            motorista.carta_conducao = request.data['carta_conducao']

        # Fotos de documentos — quando envia nova foto, marca como não verificado
        if 'foto_bi_frente' in request.FILES:
            motorista.foto_bi_frente = request.FILES['foto_bi_frente']
            motorista.bi_verificado = False
        if 'foto_bi_verso' in request.FILES:
            motorista.foto_bi_verso = request.FILES['foto_bi_verso']
            motorista.bi_verificado = False
        if 'foto_carta_frente' in request.FILES:
            motorista.foto_carta_frente = request.FILES['foto_carta_frente']
            motorista.carta_verificado = False
        if 'foto_carta_verso' in request.FILES:
            motorista.foto_carta_verso = request.FILES['foto_carta_verso']
            motorista.carta_verificado = False
        if 'foto_livrete' in request.FILES:
            motorista.foto_livrete = request.FILES['foto_livrete']
            motorista.livrete_verificado = False

        if 'foto_perfil' in request.FILES:
            motorista.foto_perfil = request.FILES['foto_perfil']   

        motorista.save()

        # Veículo
        veiculo = motorista.veiculo
        if veiculo:
            if 'veiculo_modelo' in request.data:
                veiculo.modelo = request.data['veiculo_modelo']
            if 'veiculo_placa' in request.data:
                veiculo.placa = request.data['veiculo_placa']
            if 'veiculo_capacidade' in request.data:
                veiculo.capacidade_kg = request.data['veiculo_capacidade']
            if 'veiculo_cor' in request.data:
                veiculo.cor = request.data['veiculo_cor']
            if 'foto_placa' in request.FILES:
                veiculo.foto_placa = request.FILES['foto_placa']
            if 'foto_veiculo' in request.FILES:
                veiculo.foto_veiculo = request.FILES['foto_veiculo']
            veiculo.save()

        return Response({
            "mensagem": "Perfil actualizado com sucesso!",
            "bi_verificado": motorista.bi_verificado,
            "carta_verificado": motorista.carta_verificado,
            "livrete_verificado": motorista.livrete_verificado,
            "novo_token": token_actualizado,  # None se a password não foi alterada
        })
    
class EditarPerfilClienteView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'cliente'):
            return Response({"erro": "Não é cliente."}, status=403)

        cliente = user.cliente

        # Dados do utilizador Django
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
            user.save()
            Token.objects.filter(user=user).delete()
            novo_token = Token.objects.create(user=user)
            token_actualizado = novo_token.key
        else:
            user.save()
            token_actualizado = None
        if 'telefone' in request.data:
            cliente.telefone = request.data['telefone']
        if 'endereco' in request.data:
            cliente.endereco = request.data['endereco']
        if 'bi' in request.data:
            cliente.bi = request.data['bi']
        if 'foto_perfil' in request.FILES:
            cliente.foto_perfil = request.FILES['foto_perfil']
        cliente.save()

        return Response({
            "mensagem": "Perfil actualizado com sucesso!",
            "novo_token": token_actualizado,  # None se a password não foi alterada
        })
    


class LogoutView(APIView):
    """
    Apaga o token do utilizador — resolve o problema de token persistente
    quando a app reinicia ou crasha.
    Endpoint: POST /api/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            Token.objects.filter(user=request.user).delete()
            return Response({"mensagem": "Logout efectuado com sucesso."})
        except Exception as e:
            return Response({"erro": str(e)}, status=400)