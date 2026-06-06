from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils import timezone

from core.models import pessoa, livro, emprestimo
from recomendador.models import LivroEmbedding, RequisicaoIaLog
from recomendador.services import recomendar_livros, _carregar_matriz
from recomendador.chat.interface import responder_pergunta
from .serializers import PessoaSerializer, LivroSerializer, EmprestimoSerializer
from .permissions import IsBibliotecarioOrReadOnly


class PessoaViewSet(viewsets.ModelViewSet):
    queryset = pessoa.objects.all()
    serializer_class = PessoaSerializer
    permission_classes = [IsBibliotecarioOrReadOnly]


class LivroViewSet(viewsets.ModelViewSet):
    queryset = livro.objects.all()
    serializer_class = LivroSerializer
    permission_classes = [IsBibliotecarioOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(autor__icontains=q))
        return qs


class EmprestimoViewSet(viewsets.ModelViewSet):
    queryset = emprestimo.objects.all()
    serializer_class = EmprestimoSerializer
    permission_classes = [IsBibliotecarioOrReadOnly]


class RecomendacaoIAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        livro_id = request.data.get('livro_id')
        quantidade = request.data.get('quantidade', 5)

        if not livro_id:
            return Response(
                {"error": "O campo 'livro_id' e obrigatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantidade = int(quantidade)
            if quantidade <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "O campo 'quantidade' deve ser um numero inteiro positivo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            alvo_emb = LivroEmbedding.objects.get(livro_id=livro_id)
        except LivroEmbedding.DoesNotExist:
            # Se o livro existe mas não tem embedding, retorna lista vazia
            if livro.objects.filter(pk=livro_id).exists():
                l_obj = livro.objects.get(pk=livro_id)
                response_data = {
                    "livro_origem": {"id": l_obj.id, "titulo": l_obj.titulo},
                    "recomendacoes": []
                }
                # Grava log
                RequisicaoIaLog.objects.create(
                    usuario=request.user,
                    tipo_servico='RECOMENDACAO',
                    entrada={"livro_id": livro_id, "quantidade": quantidade},
                    saida=response_data
                )
                return Response(response_data)
            return Response(
                {"error": "Livro de origem nao encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Buscar livros recomendados
        recomendados = recomendar_livros(livro_id, top_k=quantidade)

        # Calcular scores de similaridade cosseno
        matriz, ids = _carregar_matriz()
        vetor_alvo = alvo_emb.as_numpy
        scores = {}

        if matriz.size > 0:
            import numpy as np
            with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
                calculated_scores = matriz @ vetor_alvo.reshape(-1)
            for i, lid in enumerate(ids):
                scores[lid] = float(calculated_scores[i])

        recomendacoes_lista = []
        for r in recomendados:
            recomendacoes_lista.append({
                "id": r.id,
                "titulo": r.titulo,
                "autor": r.autor,
                "score_similaridade": round(scores.get(r.id, 0.0), 3)
            })

        response_data = {
            "livro_origem": {"id": alvo_emb.livro.id, "titulo": alvo_emb.livro.titulo},
            "recomendacoes": recomendacoes_lista
        }

        # Gravar log para auditoria
        RequisicaoIaLog.objects.create(
            usuario=request.user,
            tipo_servico='RECOMENDACAO',
            entrada={"livro_id": livro_id, "quantidade": quantidade},
            saida=response_data
        )

        return Response(response_data)


class ChatIAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        pergunta = request.data.get('pergunta', '').strip()

        if not pergunta:
            return Response(
                {"error": "O campo 'pergunta' e obrigatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resp = responder_pergunta(pergunta)
            
            # Carregar obras citadas ordenadas pelo retorno da IA
            obras = list(livro.objects.filter(pk__in=resp.obras_citadas))
            ordem = {lid: i for i, lid in enumerate(resp.obras_citadas)}
            obras.sort(key=lambda o: ordem.get(o.pk, 999))
            
            obras_citadas_data = [{"id": o.id, "titulo": o.titulo} for o in obras]
            
            response_data = {
                "pergunta": pergunta,
                "resposta": resp.texto,
                "obras_citadas": obras_citadas_data,
                "timestamp": timezone.now().isoformat()
            }

            # Gravar log para auditoria
            RequisicaoIaLog.objects.create(
                usuario=request.user,
                tipo_servico='CHAT',
                entrada={"pergunta": pergunta},
                saida=response_data
            )

            return Response(response_data)
        except Exception as e:
            return Response(
                {"error": f"Falha no processamento do Chat: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardClienteView(TemplateView):
    template_name = 'api/dashboard_cliente.html'
