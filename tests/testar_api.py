import sys
import os
import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Cores ANSI para o terminal (funciona no PowerShell do Windows moderno)
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Desativa prints de cores se o terminal não suportar e força codificação UTF-8 para evitar erros de unicode
if sys.platform == "win32":
    os.system("color")
    # Força UTF-8 nos fluxos de saída padrão no Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def print_header(title):
    print(f"\n{BOLD}{BLUE}=================================================================={RESET}")
    print(f"{BOLD}{BLUE} {title.upper()}{RESET}")
    print(f"{BOLD}{BLUE}=================================================================={RESET}")

def print_response(response, description, expected_status=None):
    print(f"\n{BOLD}Ação:{RESET} {description}")
    print(f"{BOLD}URL:{RESET} {response.url}")
    print(f"{BOLD}Método:{RESET} {response.request.method}")
    
    is_expected = True
    if expected_status:
        if isinstance(expected_status, list):
            is_expected = response.status_code in expected_status
        else:
            is_expected = response.status_code == expected_status
            
    status_color = GREEN if is_expected else RED
    print(f"{BOLD}Status Code:{RESET} {status_color}{response.status_code} {response.reason}{RESET}")
    
    print(f"{BOLD}Resposta JSON:{RESET}")
    try:
        formatted_json = json.dumps(response.json(), indent=2, ensure_ascii=False)
        # Limita visualização de respostas muito grandes
        if len(formatted_json) > 1000:
            print(formatted_json[:1000] + f"\n... (resposta truncada em {len(formatted_json)} caracteres) ...")
        else:
            print(formatted_json)
    except ValueError:
        # Se for texto puro (ex: YAML do schema)
        if len(response.text) > 500:
            print(response.text[:500] + f"\n... (resposta de texto truncada) ...")
        else:
            print(response.text)
            
    if expected_status and not is_expected:
        raise AssertionError(f"Erro no teste: Status esperado {expected_status}, mas obteve {response.status_code}")

def testar_api():
    print(f"{BOLD}{CYAN}Iniciando a validação de TODOS os endpoints que constam no Swagger...{RESET}")
    print(f"{BOLD}Servidor alvo:{RESET} {BASE_URL}")

    # Verificar se o servidor está rodando
    try:
        requests.get(f"{BASE_URL}/schema/", timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"\n{BOLD}{RED}[ERRO DE CONEXÃO]{RESET} O servidor local não está respondendo em {BASE_URL}.")
        print(f"Por favor, certifique-se de iniciar o Django rodando o comando:")
        print(f"{YELLOW}python manage.py runserver{RESET} no diretório 'biblioteca-django-rag'.")
        return

    # Variáveis para limpeza de dados temporários
    livro_criado_id = None
    pessoa_criada_id = None
    emprestimo_criado_id = None
    headers = {}

    try:
        # ==========================================
        # 1. TESTES DE AUTENTICAÇÃO (SEGURANÇA & JWT)
        # ==========================================
        print_header("1. Segurança e Autenticação JWT")

        # 1.1 Tentar ler o acervo de livros sem token JWT (Cenário Inválido - Esperado 401)
        url_livros = f"{BASE_URL}/livros/"
        res_unauth = requests.get(url_livros)
        print_response(res_unauth, "Ler livros sem token JWT (Esperado 401)", expected_status=401)

        # 1.2 Login com credenciais incorretas (Cenário Inválido - Esperado 401)
        url_login = f"{BASE_URL}/auth/token/"
        payload_login_fail = {"username": "admin", "password": "senha_errada"}
        res_login_fail = requests.post(url_login, json=payload_login_fail)
        print_response(res_login_fail, "Efetuar login com credenciais incorretas (Esperado 401)", expected_status=401)

        # 1.3 Login com credenciais corretas (Cenário Válido - Esperado 200)
        payload_login_ok = {"username": "admin", "password": "admin123"}
        res_login_ok = requests.post(url_login, json=payload_login_ok)
        print_response(res_login_ok, "Efetuar login com credenciais de admin (Esperado 200)", expected_status=200)
        
        login_data = res_login_ok.json()
        token_acesso_inicial = login_data["access"]
        token_atualizacao = login_data["refresh"]

        # 1.4 Testar atualização de token (Refresh Token) (Cenário Válido - Esperado 200)
        url_refresh = f"{BASE_URL}/auth/token/refresh/"
        payload_refresh = {"refresh": token_atualizacao}
        res_refresh = requests.post(url_refresh, json=payload_refresh)
        print_response(res_refresh, "Atualizar token de acesso via Refresh Token (Esperado 200)", expected_status=200)
        
        # A partir daqui, usaremos o novo token de acesso gerado no Refresh
        novo_token_acesso = res_refresh.json()["access"]
        headers = {"Authorization": f"Bearer {novo_token_acesso}"}

        # ==========================================
        # 1.5 LIMPEZA PRÉVIA (GARANTIA DE IDEMPOTÊNCIA)
        # ==========================================
        print("\nEfetuando limpeza prévia de resíduos de testes anteriores...")
        url_emprestimos = f"{BASE_URL}/emprestimos/"
        res_emps = requests.get(f"{url_emprestimos}?page_size=1000", headers=headers)
        if res_emps.status_code == 200:
            emps_data = res_emps.json()
            emps = emps_data.get("results", emps_data) if isinstance(emps_data, dict) else emps_data
            for emp in emps:
                livro_det = emp.get("livro_detalhe", {})
                leitor_det = emp.get("leitor_detalhe", {})
                if "Teste Automatizado" in livro_det.get("titulo", "") or "Teste Automatizado" in leitor_det.get("nome", ""):
                    emp_id = emp["id"]
                    print(f"Excluindo empréstimo residual (ID: {emp_id})...")
                    requests.delete(f"{url_emprestimos}{emp_id}/", headers=headers)

        url_pessoas = f"{BASE_URL}/pessoas/"
        res_pess = requests.get(f"{url_pessoas}?page_size=1000", headers=headers)
        if res_pess.status_code == 200:
            pess_data = res_pess.json()
            pess = pess_data.get("results", pess_data) if isinstance(pess_data, dict) else pess_data
            for p in pess:
                if "Teste Automatizado" in p.get("nome", "") or p.get("email") == "carlos.teste@email.com":
                    p_id = p["id"]
                    print(f"Excluindo pessoa residual (ID: {p_id})...")
                    requests.delete(f"{url_pessoas}{p_id}/", headers=headers)

        res_livs = requests.get(f"{url_livros}?q=Teste+Automatizado&page_size=1000", headers=headers)
        if res_livs.status_code == 200:
            livs_data = res_livs.json()
            livs = livs_data.get("results", livs_data) if isinstance(livs_data, dict) else livs_data
            for l in livs:
                if "Teste Automatizado" in l.get("titulo", "") or l.get("isbn") == "978-8575222287":
                    l_id = l["id"]
                    print(f"Excluindo livro residual (ID: {l_id})...")
                    requests.delete(f"{url_livros}{l_id}/", headers=headers)

        # ==========================================
        # 2. ESQUEMA OPENAPI / SWAGGER
        # ==========================================
        print_header("2. Esquema OpenAPI / Swagger")

        # 2.1 Baixar definição do esquema da API (Cenário Válido - Esperado 200)
        url_schema = f"{BASE_URL}/schema/"
        res_schema = requests.get(url_schema, headers=headers)
        print_response(res_schema, "Obter esquema OpenAPI da API (Esperado 200)", expected_status=200)

        # ==========================================
        # 3. CRUD DE PESSOAS
        # ==========================================
        print_header("3. CRUD de Pessoas (Leitores / Bibliotecários)")

        # 3.1 Listar pessoas - Paginado (Cenário Válido - Esperado 200)
        url_pessoas = f"{BASE_URL}/pessoas/"
        res_list_pessoas = requests.get(url_pessoas, headers=headers)
        print_response(res_list_pessoas, "Listar pessoas cadastradas (Esperado 200)", expected_status=200)

        # 3.2 Tentar cadastrar pessoa com celular inválido (Cenário Inválido - Esperado 400)
        payload_pessoa_fail = {
            "nome": "Leitor de Teste Inválido",
            "email": "invalido@email.com",
            "celular": "99",  # Curto demais
            "funcao": "Leitor",
            "ativo": True
        }
        res_pessoa_fail = requests.post(url_pessoas, json=payload_pessoa_fail, headers=headers)
        print_response(res_pessoa_fail, "Tentar cadastrar pessoa com celular inválido (Esperado 400)", expected_status=400)

        # 3.3 Cadastrar pessoa com dados válidos (Cenário Válido - Esperado 201)
        payload_pessoa_ok = {
            "nome": "Carlos Silva (Teste Automatizado)",
            "email": "carlos.teste@email.com",
            "celular": "62 98888-7777",
            "funcao": "Leitor",
            "nascimento": "1995-04-10",
            "ativo": True
        }
        res_pessoa_ok = requests.post(url_pessoas, json=payload_pessoa_ok, headers=headers)
        print_response(res_pessoa_ok, "Cadastrar pessoa com dados e celular corretos (Esperado 201)", expected_status=201)
        pessoa_criada_id = res_pessoa_ok.json()["id"]

        # 3.4 Ler detalhes da pessoa criada (Cenário Válido - Esperado 200)
        url_pessoa_detalhe = f"{url_pessoas}{pessoa_criada_id}/"
        res_get_pessoa = requests.get(url_pessoa_detalhe, headers=headers)
        print_response(res_get_pessoa, "Obter detalhes da pessoa recém-criada (Esperado 200)", expected_status=200)

        # 3.5 Atualização Completa (PUT) da pessoa (Cenário Válido - Esperado 200)
        payload_pessoa_put = {
            "nome": "Carlos Silva Atualizado (PUT)",
            "email": "carlos.atualizado@email.com",
            "celular": "62 99999-8888",
            "funcao": "Leitor",
            "nascimento": "1995-04-10",
            "ativo": True
        }
        res_put_pessoa = requests.put(url_pessoa_detalhe, json=payload_pessoa_put, headers=headers)
        print_response(res_put_pessoa, "Atualizar dados da pessoa via PUT completo (Esperado 200)", expected_status=200)

        # 3.6 Atualização Parcial (PATCH) da pessoa (Cenário Válido - Esperado 200)
        payload_pessoa_patch = {
            "celular": "62 91111-2222"
        }
        res_patch_pessoa = requests.patch(url_pessoa_detalhe, json=payload_pessoa_patch, headers=headers)
        print_response(res_patch_pessoa, "Atualizar parcialmente celular da pessoa via PATCH (Esperado 200)", expected_status=200)

        # ==========================================
        # 4. CRUD DE LIVROS
        # ==========================================
        print_header("4. CRUD de Livros (Obras)")

        # 4.1 Listar livros - Paginado (Cenário Válido - Esperado 200)
        res_list_livros = requests.get(url_livros, headers=headers)
        print_response(res_list_livros, "Listar livros cadastrados (Esperado 200)", expected_status=200)

        # 4.2 Tentar cadastrar livro com ISBN inválido (Cenário Inválido - Esperado 400)
        payload_livro_fail = {
            "titulo": "Código Invalido",
            "autor": "GoF",
            "tipo_obra": "BIBLIOGRAFIA",
            "isbn": "ISBN-INVALIDO",
            "ano": 2020,
            "exemplares_total": 5,
            "exemplares_disponiveis": 5
        }
        res_livro_fail = requests.post(url_livros, json=payload_livro_fail, headers=headers)
        print_response(res_livro_fail, "Tentar cadastrar livro com ISBN inválido (Esperado 400)", expected_status=400)

        # 4.3 Cadastrar livro com dados válidos (Cenário Válido - Esperado 201)
        payload_livro_ok = {
            "titulo": "Código Limpo (Teste Automatizado)",
            "autor": "Robert C. Martin",
            "tipo_obra": "BIBLIOGRAFIA",
            "isbn": "978-8575222287",  # ISBN-13 válido
            "ano": 2012,
            "exemplares_total": 4,
            "exemplares_disponiveis": 4
        }
        res_livro_ok = requests.post(url_livros, json=payload_livro_ok, headers=headers)
        print_response(res_livro_ok, "Cadastrar livro com dados e ISBN válidos (Esperado 201)", expected_status=201)
        livro_criado_id = res_livro_ok.json()["id"]

        # 4.4 Ler detalhes do livro criado (Cenário Válido - Esperado 200)
        url_livro_detalhe = f"{url_livros}{livro_criado_id}/"
        res_get_livro = requests.get(url_livro_detalhe, headers=headers)
        print_response(res_get_livro, "Obter detalhes do livro recém-criado (Esperado 200)", expected_status=200)

        # 4.5 Atualização Completa (PUT) do livro (Cenário Válido - Esperado 200)
        payload_livro_put = {
            "titulo": "Código Limpo Atualizado (PUT)",
            "autor": "Robert C. Martin",
            "tipo_obra": "BIBLIOGRAFIA",
            "isbn": "978-8575222287",
            "ano": 2015,
            "exemplares_total": 5,
            "exemplares_disponiveis": 5
        }
        res_put_livro = requests.put(url_livro_detalhe, json=payload_livro_put, headers=headers)
        print_response(res_put_livro, "Atualizar dados do livro via PUT completo (Esperado 200)", expected_status=200)

        # 4.6 Atualização Parcial (PATCH) do livro (Cenário Válido - Esperado 200)
        payload_livro_patch = {
            "exemplares_disponiveis": 3  # Simulando retirada manual ou reserva
        }
        res_patch_livro = requests.patch(url_livro_detalhe, json=payload_livro_patch, headers=headers)
        print_response(res_patch_livro, "Atualizar parcialmente exemplares do livro via PATCH (Esperado 200)", expected_status=200)

        # ==========================================
        # 5. CRUD DE EMPRÉSTIMOS
        # ==========================================
        print_header("5. CRUD de Empréstimos")

        # 5.1 Listar empréstimos - Paginado (Cenário Válido - Esperado 200)
        url_emprestimos = f"{BASE_URL}/emprestimos/"
        res_list_emprestimos = requests.get(url_emprestimos, headers=headers)
        print_response(res_list_emprestimos, "Listar empréstimos cadastrados (Esperado 200)", expected_status=200)

        # 5.2 Cadastrar empréstimo válido (Cenário Válido - Esperado 201)
        payload_emp_ok = {
            "livro": livro_criado_id,
            "leitor": pessoa_criada_id
        }
        res_emp_ok = requests.post(url_emprestimos, json=payload_emp_ok, headers=headers)
        print_response(res_emp_ok, "Cadastrar empréstimo com livro e leitor válidos (Esperado 201)", expected_status=201)
        emprestimo_criado_id = res_emp_ok.json()["id"]

        # 5.3 Ler detalhes do empréstimo criado (Cenário Válido - Esperado 200)
        url_emp_detalhe = f"{url_emprestimos}{emprestimo_criado_id}/"
        res_get_emp = requests.get(url_emp_detalhe, headers=headers)
        print_response(res_get_emp, "Obter detalhes do empréstimo recém-criado (Esperado 200)", expected_status=200)

        # 5.4 Atualização Completa (PUT) do empréstimo (Cenário Válido - Esperado 200)
        payload_emp_put = {
            "livro": livro_criado_id,
            "leitor": pessoa_criada_id,
            "data_devolucao_real": None
        }
        res_put_emp = requests.put(url_emp_detalhe, json=payload_emp_put, headers=headers)
        print_response(res_put_emp, "Atualizar empréstimo via PUT (Esperado 200)", expected_status=200)

        # 5.5 Atualização Parcial (PATCH) - Efetuar devolução real da obra (Cenário Válido - Esperado 200)
        payload_emp_patch = {
            "data_devolucao_real": date.today().isoformat()
        }
        res_patch_emp = requests.patch(url_emp_detalhe, json=payload_emp_patch, headers=headers)
        print_response(res_patch_emp, "Marcar data de devolução real via PATCH (Esperado 200)", expected_status=200)

        # ==========================================
        # 6. SERVIÇOS COGNITIVOS DE IA (RECOMENDAÇÃO E CHAT)
        # ==========================================
        print_header("6. Serviços Cognitivos de IA")

        # 6.1 Recomendação Semântica Cosseno (Cenário Válido - Esperado 200)
        url_rec = f"{BASE_URL}/ia/recomendar/"
        payload_rec = {"livro_id": livro_criado_id, "quantidade": 3}
        res_rec = requests.post(url_rec, json=payload_rec, headers=headers)
        print_response(res_rec, "Solicitar recomendação semântica cosseno de IA (Esperado 200)", expected_status=200)

        # 6.2 Chat RAG Conversacional com Groq/Llama (Cenário Válido - Esperado 200)
        url_chat = f"{BASE_URL}/ia/chat/"
        payload_chat = {"pergunta": "Quais livros tratam de desenvolvimento de software e programação limpa no acervo?"}
        print(f"\n{BOLD}Ação:{RESET} Enviar pergunta ao Chat RAG. Aguardando processamento da IA...")
        res_chat = requests.post(url_chat, json=payload_chat, headers=headers)
        print_response(res_chat, "Enviar pergunta legítima ao Chat RAG (Esperado 200)", expected_status=200)

    except Exception as e:
        print(f"\n{BOLD}{RED}[ERRO DURANTE OS TESTES]{RESET} {str(e)}")
        raise e

    finally:
        # ==========================================
        # 7. LIMPEZA DE DADOS DE TESTE
        # ==========================================
        print_header("7. Limpeza Geral de Dados de Teste")
        
        # Garante que os registros sejam excluídos na ordem reversa de dependência
        if emprestimo_criado_id and headers:
            url_delete_emp = f"{url_emprestimos}{emprestimo_criado_id}/"
            res_delete_emp = requests.delete(url_delete_emp, headers=headers)
            print(f"Removendo Empréstimo temporário (ID: {emprestimo_criado_id}): Status {res_delete_emp.status_code}")

        if pessoa_criada_id and headers:
            url_delete_pes = f"{url_pessoas}{pessoa_criada_id}/"
            res_delete_pes = requests.delete(url_delete_pes, headers=headers)
            print(f"Removendo Pessoa temporária (ID: {pessoa_criada_id}): Status {res_delete_pes.status_code}")

        if livro_criado_id and headers:
            url_delete_liv = f"{url_livros}{livro_criado_id}/"
            res_delete_liv = requests.delete(url_delete_liv, headers=headers)
            print(f"Removendo Livro temporário (ID: {livro_criado_id}): Status {res_delete_liv.status_code}")

        print(f"\n{BOLD}{GREEN}=================================================================={RESET}")
        print(f"{BOLD}{GREEN} VALIDAÇÃO CONCLUÍDA! TODOS OS ENDPOINTS DO SWAGGER FORAM TESTADOS.{RESET}")
        print(f"{BOLD}{GREEN}=================================================================={RESET}\n")

if __name__ == "__main__":
    testar_api()
