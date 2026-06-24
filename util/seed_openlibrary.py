import os
import sys

# Ajusta o caminho para carregar o Django (adjusted for subfolder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblioteca_mvp.settings')

import django
django.setup()

import requests
import random
from datetime import date, timedelta
from faker import Faker
from core.models import pessoa, livro, emprestimo

fake = Faker('pt_BR')

def get_openlibrary_books(limit=1000):
    url = f"https://openlibrary.org/search.json?q=programming+science+history+fiction&limit={limit}"
    print(f"Buscando {limit} livros na OpenLibrary...")
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('docs', [])
    print("Falha ao buscar livros.")
    return []

def seed_openlibrary_data(limit_books=200):
    docs = get_openlibrary_books(limit=limit_books)
    if not docs:
        print("Nenhum livro para inserir.")
        return

    # Garante grupos e usuários básicos
    from django.contrib.auth.models import User, Group, Permission
    User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True, 'email': 'admin@test.com'})
    
    # Criar 200 leitores falsos
    print("Gerando 200 leitores...")
    for _ in range(200):
        nome = fake.name()
        email = fake.unique.email()
        celular = fake.cellphone_number()
        # Garante tamanho correto conforme validação do model
        import re
        celular_clean = re.sub(r'\D', '', celular)
        if len(celular_clean) not in (10, 11):
            celular_clean = f"6299999{random.randint(1000, 9999)}"
        
        pessoa.objects.create(
            nome=nome,
            email=email,
            celular=celular_clean,
            funcao='Leitor',
            ativo=random.choice([True, True, True, False]) # 25% inativo
        )

    # Inserir livros
    print("Inserindo livros da OpenLibrary no banco...")
    livros_inseridos = 0
    
    tipos = ['BIBLIOGRAFIA', 'TESE_DISSERTACAO', 'MONOGRAFIA']
    
    for doc in docs:
        if livros_inseridos >= limit_books:
            break
            
        titulo = doc.get('title')
        autores = doc.get('author_name', ['Autor Desconhecido'])
        autor = autores[0] if autores else 'Autor Desconhecido'
        ano = doc.get('first_publish_year', random.randint(2000, 2025))
        
        isbn = None
        if doc.get('isbn'):
            isbn = doc.get('isbn')[0][:20]
            
        tipo_obra = random.choice(tipos)
        
        # Garante ISBN de 13 dígitos numéricos válido para passar na nova validação se for Bibliografia
        if tipo_obra == 'BIBLIOGRAFIA':
            # Limpa o ISBN retornado ou gera um numérico se inválido
            if isbn:
                isbn_clean = ''.join(c for c in isbn if c.isdigit())
                if len(isbn_clean) not in (10, 13):
                    # Gera um fictício de 13 dígitos
                    isbn_clean = f"97899900{random.randint(10000, 99999):05d}"
            else:
                isbn_clean = f"97899900{random.randint(10000, 99999):05d}"
            isbn = isbn_clean
        else:
            # Para Teses/Monografias, limpa apenas se existir
            if isbn:
                isbn = ''.join(c for c in isbn if c.isdigit())[:20] or None

        total_ex = random.randint(1, 10)
        
        # Garante título e autor curtos para não estourar CharField
        titulo = titulo[:200]
        autor = autor[:100]

        try:
            livro.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'autor': autor,
                    'tipo_obra': tipo_obra,
                    'isbn': isbn,
                    'ano': ano,
                    'exemplares_total': total_ex,
                    'exemplares_disponiveis': total_ex
                }
            )
            livros_inseridos += 1
        except Exception as e:
            # Pula em caso de erro (ex: ISBN duplicado)
            continue

    print(f"Livros cadastrados com sucesso: {livros_inseridos}")

    # Gerar 1200 empréstimos aleatórios
    print("Gerando 1200 empréstimos históricos...")
    leitores = list(pessoa.objects.filter(funcao='Leitor'))
    livros_disponiveis = list(livro.objects.all())
    
    if not leitores or not livros_disponiveis:
        print("Impossível gerar empréstimos sem leitores ou livros.")
        return

    emprestimos_gerados = 0
    while emprestimos_gerados < 1200:
        l = random.choice(leitores)
        b = random.choice(livros_disponiveis)
        
        # Simula datas passadas
        dias_atras = random.randint(1, 180)
        data_s = date.today() - timedelta(days=dias_atras)
        data_p = data_s + timedelta(days=14)
        
        # Define se já foi devolvido
        devolvido = random.choice([True, True, True, False]) # 75% devolvido
        data_r = None
        if devolvido:
            # devolvido com atraso ou em dia
            dias_para_devolver = random.randint(5, 20)
            data_r = data_s + timedelta(days=dias_para_devolver)
            
        # Cria empréstimo burlando o save() para não mexer no estoque atual do banco
        # para simular histórico legado consistente
        emp = emprestimo(
            livro=b,
            leitor=l,
            data_saida=data_s,
            data_devolucao_prevista=data_p,
            data_devolucao_real=data_r
        )
        try:
            # Usa save_base para contornar a validação e o decremento dinâmico de estoque transacional
            emp.save_base(raw=True)
            emprestimos_gerados += 1
        except Exception:
            continue

    print(f"Histórico populado com {emprestimos_gerados} empréstimos.")

if __name__ == '__main__':
    seed_openlibrary_data(limit_books=250)
