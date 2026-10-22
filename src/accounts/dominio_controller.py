from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.dominios import (
    carregar_alvo,
    concessoes_diretas,
    concessoes_herdadas,
    dominios_ativos,
    nome_dominio,
    pode_gerenciar,
)
from accounts.models import NIVEIS_DOMINIO, DominioAcesso


def _nome_alvo(nivel: str, alvo) -> str:
    return alvo.email if nivel == "usuario" else alvo.nome


class DominiosDisponiveisView(APIView):
    """Lista os domínios de dados da IA que podem receber concessão."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "success": True,
                "data": [{"chave": chave, "nome": nome_dominio(chave)} for chave in dominios_ativos()],
            }
        )


class DominioAcessoView(APIView):
    """Concessões de domínio de um alvo (empresa, filial, setor ou usuário).

    GET  ?nivel=empresa&alvo=3  -> concessões diretas e herdadas do alvo
    POST {dominio, nivel, alvo} -> concede o domínio ao alvo e a tudo abaixo dele
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        nivel = request.query_params.get("nivel", "")
        alvo_id = request.query_params.get("alvo", "")
        alvo = self._buscar_alvo(nivel, alvo_id)
        if alvo is None:
            return Response({"success": False, "error": "Alvo inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if not pode_gerenciar(request.user, nivel, alvo):
            return Response(
                {"success": False, "error": "Permissão insuficiente para este alvo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "alvo": {"nivel": nivel, "id": alvo.pk, "nome": _nome_alvo(nivel, alvo)},
                    "diretos": [
                        {"id": c.pk, "dominio": c.dominio, "nome": nome_dominio(c.dominio)}
                        for c in concessoes_diretas(nivel, alvo)
                    ],
                    "herdados": [
                        {**item, "nome": nome_dominio(item["dominio"])}
                        for item in concessoes_herdadas(nivel, alvo)
                    ],
                    "dominios_ativos": [
                        {"chave": chave, "nome": nome_dominio(chave)} for chave in dominios_ativos()
                    ],
                },
            }
        )

    def post(self, request):
        dominio = str(request.data.get("dominio", "")).strip()
        nivel = str(request.data.get("nivel", "")).strip()
        alvo_id = request.data.get("alvo")

        if dominio not in dominios_ativos():
            return Response({"success": False, "error": "Domínio inválido."}, status=status.HTTP_400_BAD_REQUEST)
        alvo = self._buscar_alvo(nivel, alvo_id)
        if alvo is None:
            return Response({"success": False, "error": "Alvo inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if not pode_gerenciar(request.user, nivel, alvo):
            return Response(
                {"success": False, "error": "Permissão insuficiente para este alvo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                concessao = DominioAcesso.objects.create(dominio=dominio, **{f"{nivel}_id": alvo.pk})
        except IntegrityError:
            return Response(
                {"success": False, "error": "Este domínio já foi concedido a este alvo."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "success": True,
                "message": "Acesso concedido com sucesso",
                "data": {"id": concessao.pk, "dominio": dominio, "nivel": nivel, "alvo": alvo.pk},
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _buscar_alvo(nivel, alvo_id):
        if nivel not in NIVEIS_DOMINIO:
            return None
        try:
            return carregar_alvo(nivel, int(alvo_id))
        except (TypeError, ValueError):
            return None


class DominioAcessoDetailView(APIView):
    """Retira uma concessão direta. Concessões herdadas devem ser retiradas no nível de origem."""

    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        concessao = DominioAcesso.objects.filter(pk=pk).first()
        if concessao is None:
            return Response({"success": False, "error": "Concessão não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        alvo = carregar_alvo(concessao.nivel, concessao.alvo_id)
        if alvo is None or not pode_gerenciar(request.user, concessao.nivel, alvo):
            return Response(
                {"success": False, "error": "Permissão insuficiente para este alvo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        concessao.delete()
        return Response(
            {"success": True, "message": "Acesso retirado com sucesso"},
            status=status.HTTP_200_OK,
        )
