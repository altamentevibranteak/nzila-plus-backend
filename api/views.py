from urllib import request
from django.shortcuts import render
from rest_framework import viewsets, generics, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Carga, Motorista
from .serializers import CargaSerializer, MotoristaSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, extend_schema_view


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

    @action(detail=False, methods=['get'], url_path='disponiveis', url_name='disponiveis')
    def disponiveis(self, request):
        # SEGURANÇA: Se não for motorista, nem deixamos ver a lista
        if not hasattr(request.user, 'motorista') and not request.user.is_staff:
            return Response(
                {"erro": "Apenas motoristas podem aceder ao mercado de cargas."},
                status=status.HTTP_403_FORBIDDEN
            )

        cargas_disponiveis = Carga.objects.filter(
            status='PENDENTE', 
            motorista__isnull=True
        ).order_by('-data_criacao')
        
        serializer = self.get_serializer(cargas_disponiveis, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='aceitar', url_name='aceitar', serializer_class=EmptySerializer)
    def aceitar(self, request, pk=None):
        # 1. Busca a carga
        carga = self.get_object()
        
        # 2. Verifica se o user é motorista
        if not hasattr(request.user, 'motorista'):
            return Response({"erro": "Apenas motoristas podem aceitar cargas."}, status=403)
        
        motorista_logado = request.user.motorista

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
            
            # Em vez de: serializer = self.get_serializer(carga)
            # Usa o serializer principal para a resposta:
            serializer = CargaSerializer(carga) 
            
            return Response({
                "mensagem": "Carga aceita com sucesso!",
                "carga": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"erro": f"Erro ao salvar: {str(e)}"}, status=400)

    @action(detail=True, methods=['post'], url_path='recusar', url_name='recusar', serializer_class=EmptySerializer)
    def recusar(self, request, pk=None):
        """
        Motorista recusa uma carga disponível.
        Por enquanto, apenas retorna mensagem de sucesso.
        TODO: Adicionar lógica de ignorar/marcar como rejeitado pelo motorista.
        Endpoint: POST /api/cargas/{id}/recusar/
        
        Requer: URL com o ID da carga
        Sem campos adicionais no corpo da requisição.
        """
        try:
            # Verificar se o usuário é um Motorista
            if not hasattr(request.user, 'motorista'):
                return Response(
                    {"erro": "Apenas motoristas podem recusar cargas."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            carga = self.get_object()
        except Carga.DoesNotExist:
            return Response(
                {"erro": "Carga não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"erro": f"Erro ao recusar carga: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se a carga está com status PENDENTE
        if carga.status != 'PENDENTE':
            return Response(
                {
                    "erro": f"Esta carga não pode ser recusada. Status atual: {carga.status}",
                    "status_atual": carga.status
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Por enquanto, apenas retorna sucesso
        # TODO: Implementar lógica de rastreamento de motoristas que recusaram
        return Response(
            {
                "mensagem": "Carga recusada com sucesso!",
                "carga_id": carga.id,
                "carga_titulo": carga.titulo
            },
            status=status.HTTP_200_OK
        )

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

class MotoristaViewSet(viewsets.ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer

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