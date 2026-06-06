from django.urls import reverse
from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta

from core.models import livro, pessoa, emprestimo, PRAZO_EMPRESTIMO_DIAS
from recomendador.models import LivroEmbedding, RequisicaoIaLog


class BibliotecaApiTests(APITestCase):

    def setUp(self):
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

    def test_auth_login_jwt(self):
        """Testa a obtenção do token JWT e o refresh"""
        tokens = self.get_tokens('leitor', 'password123')
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)

        # Testar refresh
        url = reverse('token_refresh')
        response = self.client.post(url, {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_livros_crud_permissions(self):
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

    def test_emprestimo_flow_and_validation(self):
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

    def test_ia_recomendacao_endpoint(self):
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
