from django.urls import reverse
from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from unittest.mock import patch

from core.models import livro, pessoa, emprestimo, PRAZO_EMPRESTIMO_DIAS
from recomendador.models import LivroEmbedding, RequisicaoIaLog
from recomendador.chat.interface import RespostaChat


class BibliotecaApiTests(APITestCase):

    def setUp(self):
        import logging
        logging.disable(logging.WARNING)

        # Criar grupo de Bibliotecários
        self.grupo_bibliotecario = Group.objects.create(name='Bibliotecario')

        # Criar usuários de teste
        self.leitor_user = User.objects.create_user(username='leitor', password='password123')
        self.biblio_user = User.objects.create_user(username='bibliotecario', password='password123')
        self.biblio_user.groups.add(self.grupo_bibliotecario)

        # Criar entidades de pessoa (Leitor e Bibliotecário)
        self.leitor_pessoa = pessoa.objects.create(
            nome="Leitor Teste",
            email="leitor@teste.com",
            funcao="Leitor",
            ativo=True
        )
        self.biblio_pessoa = pessoa.objects.create(
            nome="Biblio Teste",
            email="biblio@teste.com",
            funcao="Bibliotecario",
            ativo=True
        )

        # Criar Livros
        self.livro1 = livro.objects.create(
            titulo="Livro Teste A",
            autor="Autor Teste A",
            tipo_obra="BIBLIOGRAFIA",
            isbn="1234567890",
            ano=2020,
            exemplares_total=5,
            exemplares_disponiveis=5
        )
        self.livro_esgotado = livro.objects.create(
            titulo="Livro Esgotado",
            autor="Autor Teste B",
            tipo_obra="MONOGRAFIA",
            exemplares_total=1,
            exemplares_disponiveis=0
        )

        # O signal post_save de livro já cria o LivroEmbedding. 
        # Vamos usar get_or_create e atualizar os dados do vetor e texto_fonte para os testes.
        import numpy as np
        dim = 384
        vetor_teste = np.zeros(dim, dtype=np.float32)
        vetor_teste[0] = 1.0  # vetor unitário normalizado
        
        self.emb1, created = LivroEmbedding.objects.get_or_create(
            livro=self.livro1,
            defaults={
                'texto_fonte': "Livro Teste A sobre programacao e Python",
                'modelo_versao': "test-model",
                'dimensao': dim,
                'vetor': vetor_teste.tobytes()
            }
        )
        if not created:
            self.emb1.set_vetor(vetor_teste)
            self.emb1.texto_fonte = "Livro Teste A sobre programacao e Python"
            self.emb1.modelo_versao = "test-model"
            self.emb1.save()

    def get_tokens(self, username, password):
        url = reverse('token_obtain_pair')
        response = self.client.post(url, {'username': username, 'password': password}, format='json')
        return response.data

    def test_01_auth_login_jwt(self):
        """Testa a obtenção do token JWT e o refresh"""
        tokens = self.get_tokens('leitor', 'password123')
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)

        # Testar refresh
        url = reverse('token_refresh')
        response = self.client.post(url, {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_02_auth_login_jwt_failed(self):
        """Testa que a obtenção de token falha com credenciais incorretas e não gera token"""
        url = reverse('token_obtain_pair')
        
        # Caso 1: Usuário correto, senha incorreta
        response = self.client.post(url, {'username': 'leitor', 'password': 'senha_errada'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        
        # Caso 2: Usuário inexistente
        response = self.client.post(url, {'username': 'usuario_inexistente', 'password': 'password123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_03_livros_crud_permissions(self):
        """Testa se o leitor comum só tem acesso a leitura (GET) e o bibliotecário pode criar (POST)"""
        # --- Cenário 1: Leitor (Apenas GET)
        tokens_leitor = self.get_tokens('leitor', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])

        # GET deve funcionar
        response = self.client.get(reverse('livro-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # POST deve ser negado (403 Forbidden)
        payload = {
            "titulo": "Novo Livro",
            "autor": "Novo Autor",
            "tipo_obra": "MONOGRAFIA",
            "exemplares_total": 2,
            "exemplares_disponiveis": 2
        }
        response = self.client.post(reverse('livro-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # --- Cenário 2: Bibliotecário (Permissão total)
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])

        response = self.client.post(reverse('livro-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(livro.objects.filter(titulo="Novo Livro").count(), 1)

    def test_04_emprestimo_flow_and_validation(self):
        """Testa criação de empréstimo, decremento de estoque e erro ao esgotar"""
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])

        # Criar empréstimo válido
        payload = {
            "livro": self.livro1.id,
            "leitor": self.leitor_pessoa.id
        }
        response = self.client.post(reverse('emprestimo-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verificar se o estoque do livro 1 diminuiu para 4
        self.livro1.refresh_from_db()
        self.assertEqual(self.livro1.exemplares_disponiveis, 4)

        # Verificar se data_devolucao_prevista é hoje + 14 dias
        emp_id = response.data['id']
        emp = emprestimo.objects.get(pk=emp_id)
        self.assertEqual(emp.data_devolucao_prevista, date.today() + timedelta(days=PRAZO_EMPRESTIMO_DIAS))

        # Tentar emprestar livro esgotado (deve retornar 400 Bad Request)
        payload_esgotado = {
            "livro": self.livro_esgotado.id,
            "leitor": self.leitor_pessoa.id
        }
        response = self.client.post(reverse('emprestimo-list'), payload_esgotado, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_05_ia_recomendacao_endpoint(self):
        """Testa a rota de recomendação de IA e a gravação de logs"""
        tokens_leitor = self.get_tokens('leitor', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])

        # Rota de recomendação
        url = reverse('ia_recomendar')
        payload = {
            "livro_id": self.livro1.id,
            "quantidade": 3
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("livro_origem", response.data)
        self.assertIn("recomendacoes", response.data)

        # Verificar se gravou no RequisicaoIaLog
        logs = RequisicaoIaLog.objects.filter(tipo_servico='RECOMENDACAO')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().usuario, self.leitor_user)

    def test_06_pessoa_celular_validation(self):
        """Testa se a validação de celular do leitor está funcionando no serializer"""
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])

        url = reverse('pessoa-list')
        
        # Caso inválido 1: Celular muito curto
        payload = {
            "nome": "Leitor Novo",
            "email": "leitor_novo@teste.com",
            "funcao": "Leitor",
            "celular": "12345",
            "ativo": True
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("celular", response.data['details'])

        # Caso inválido 2: Celular muito longo
        payload["celular"] = "6299999123456"
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso válido: Formato correto
        payload["celular"] = "62999998888"
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_07_livro_isbn_validation(self):
        """Testa se a validação técnica do ISBN está funcionando no serializer"""
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])

        url = reverse('livro-list')
        
        # Caso inválido 1: Tamanho inadequado (não tem 10 nem 13 caracteres)
        payload = {
            "titulo": "Novo Livro Teste",
            "autor": "Autor Novo",
            "tipo_obra": "BIBLIOGRAFIA",
            "isbn": "123456",
            "ano": 2021,
            "exemplares_total": 5,
            "exemplares_disponiveis": 5
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("isbn", response.data['details'])

        # Caso inválido 2: Caracteres inválidos
        payload["isbn"] = "978857522abc"
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso válido 1: ISBN-10 válido com hífen (deve ser limpo e aceito)
        payload["isbn"] = "85-7522-753-0"
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Caso válido 2: ISBN-13 válido
        payload["titulo"] = "Outro Livro Novo"
        payload["isbn"] = "9788575227534"
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_08_ia_recomendacao_validation(self):
        """Testa validação de parâmetros na API de Recomendação"""
        tokens_leitor = self.get_tokens('leitor', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])

        url = reverse('ia_recomendar')
        
        # Caso inválido 1: quantidade abaixo do limite mínimo (0)
        payload = {
            "livro_id": self.livro1.id,
            "quantidade": 0
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso inválido 2: quantidade acima do limite máximo (11)
        payload["quantidade"] = 11
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso inválido 3: livro_id ausente
        payload = {
            "quantidade": 5
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_09_ia_chat_validation(self):
        """Testa validação de perguntas na API do Chat RAG"""
        tokens_leitor = self.get_tokens('leitor', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])

        url = reverse('ia_chat')

        # Caso inválido 1: pergunta curta demais (< 3 chars)
        payload = {
            "pergunta": "oi"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Caso inválido 2: pergunta longa demais (> 1000 chars)
        payload["pergunta"] = "a" * 1001
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("A pergunta excede o limite máximo", response.data['details']['pergunta'][0])

        # Caso inválido 3: pergunta em branco
        payload["pergunta"] = ""
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('api.views.responder_pergunta')
    def test_10_ia_chat_endpoint_success(self, mock_responder):
        """Testa o sucesso do endpoint de Chat RAG da IA com mock e a gravação de logs"""
        mock_responder.return_value = RespostaChat(
            texto="Segundo o acervo, a obra 'Livro Teste A' (Obra #1) trata de programação.",
            obras_citadas=[self.livro1.id]
        )
        
        tokens_leitor = self.get_tokens('leitor', 'password123')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        
        url = reverse('ia_chat')
        payload = {"pergunta": "Quais livros tratam de programação?"}
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resposta", response.data)
        self.assertEqual(response.data['obras_citadas'][0]['id'], self.livro1.id)
        
        # Verificar se gravou no RequisicaoIaLog
        logs = RequisicaoIaLog.objects.filter(tipo_servico='CHAT')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().usuario, self.leitor_user)

    def test_11_livro_crud_full(self):
        """Testa o CRUD completo de livros e permissões associadas"""
        # Obter tokens
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        tokens_leitor = self.get_tokens('leitor', 'password123')

        # 1) GET detalhe do livro (Acessível a qualquer usuário autenticado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        url_detail = reverse('livro-detail', args=[self.livro1.id])
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['titulo'], self.livro1.titulo)

        # 2) PUT (atualização) por Bibliotecário (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        payload = {
            "titulo": "Livro Teste A Modificado",
            "autor": "Autor Modificado",
            "tipo_obra": "BIBLIOGRAFIA",
            "isbn": "1234567890",
            "ano": 2021,
            "exemplares_total": 5,
            "exemplares_disponiveis": 5
        }
        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.livro1.refresh_from_db()
        self.assertEqual(self.livro1.titulo, "Livro Teste A Modificado")

        # 3) PUT (atualização) por Leitor Comum (Negado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4) DELETE por Leitor Comum (Negado)
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 5) DELETE por Bibliotecário (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(livro.objects.filter(pk=self.livro1.id).exists())

    def test_12_pessoa_crud_full(self):
        """Testa o CRUD completo de Pessoas (leitores/bibliotecários) e permissões"""
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        tokens_leitor = self.get_tokens('leitor', 'password123')

        # 1) GET listagem por Leitor Comum (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        url_list = reverse('pessoa-list')
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2) GET detalhe por Leitor Comum (Permitido)
        url_detail = reverse('pessoa-detail', args=[self.leitor_pessoa.id])
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], self.leitor_pessoa.nome)

        # 3) PUT (atualização) por Leitor Comum (Negado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        payload = {
            "nome": "Leitor Teste Modificado",
            "email": "leitor_mod@teste.com",
            "funcao": "Leitor",
            "celular": "62999998888",
            "ativo": True
        }
        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4) PUT (atualização) por Bibliotecário (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.leitor_pessoa.refresh_from_db()
        self.assertEqual(self.leitor_pessoa.nome, "Leitor Teste Modificado")

        # 5) DELETE por Leitor Comum (Negado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 6) DELETE por Bibliotecário (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(pessoa.objects.filter(pk=self.leitor_pessoa.id).exists())

    def test_13_emprestimo_crud_full(self):
        """Testa o CRUD completo e ciclo de devolução dos Empréstimos"""
        tokens_biblio = self.get_tokens('bibliotecario', 'password123')
        tokens_leitor = self.get_tokens('leitor', 'password123')

        # Criar empréstimo inicial para testar detalhe, alteração e exclusão
        emp_inicial = emprestimo.objects.create(livro=self.livro1, leitor=self.leitor_pessoa)

        # 1) GET listagem por Leitor Comum (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        url_list = reverse('emprestimo-list')
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2) GET detalhe por Leitor Comum (Permitido)
        url_detail = reverse('emprestimo-detail', args=[emp_inicial.id])
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['livro'], self.livro1.id)

        # 3) PUT (Devolução - alterando data_devolucao_real) por Leitor Comum (Negado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        payload = {
            "livro": self.livro1.id,
            "leitor": self.leitor_pessoa.id,
            "data_devolucao_real": str(date.today())
        }
        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4) PUT (Devolução - alterando data_devolucao_real) por Bibliotecário (Permitido e repõe estoque)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        
        # Antes da devolução, estoque deve refletir o empréstimo (diminuiu para 4 na criação do setup + 1 para este teste = 3)
        self.livro1.refresh_from_db()
        estoque_antes = self.livro1.exemplares_disponiveis

        response = self.client.put(url_detail, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Estoque deve ter incrementado de volta após devolução
        self.livro1.refresh_from_db()
        self.assertEqual(self.livro1.exemplares_disponiveis, estoque_antes + 1)
        self.assertEqual(response.data['status'], 'DEVOLVIDO')

        # 5) DELETE por Leitor Comum (Negado)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_leitor['access'])
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 6) DELETE por Bibliotecário (Permitido)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens_biblio['access'])
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(emprestimo.objects.filter(pk=emp_inicial.id).exists())
