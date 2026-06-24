import os
import sys
import django
import re

# Setup Django (adjusted for subfolder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblioteca_mvp.settings')
django.setup()

from core.models import pessoa, livro, emprestimo

def validar_celular(value):
    if not value:
        return True, "Válido (Vazio)"
    digits = re.sub(r'\D', '', value)
    if len(digits) < 10 or len(digits) > 11:
        return False, f"Tamanho inválido ({len(digits)} dígitos, esperado 10 ou 11)"
    return True, "Válido"

def run_audit():
    print("=== AUDITORIA GERAL DO BANCO DE DADOS ===")
    
    # 1. Auditoria de Pessoas
    pessoas = pessoa.objects.all()
    pessoas_invalidas = []
    print(f"\nAuditando {len(pessoas)} pessoas...")
    for p in pessoas:
        cel_ok, cel_msg = validar_celular(p.celular)
        func_ok = p.funcao in ['Leitor', 'Bibliotecario']
        
        erros = []
        if not cel_ok:
            erros.append(f"Celular inválido ('{p.celular}': {cel_msg})")
        if not func_ok:
            erros.append(f"Função inválida ('{p.funcao}', esperado Leitor/Bibliotecario)")
            
        if erros:
            pessoas_invalidas.append((p, erros))
            
    print(f"Pessoas com inconsistências encontradas: {len(pessoas_invalidas)}")
    for p, erros in pessoas_invalidas:
        print(f"  - [Pessoa ID {p.pk}] '{p.nome}' | Erros: {', '.join(erros)}")
        
    # 2. Auditoria de Livros
    livros = livro.objects.all()
    livros_invalidos = []
    print(f"\nAuditando {len(livros)} livros...")
    for l in livros:
        erros = []
        if l.exemplares_disponiveis > l.exemplares_total:
            erros.append(f"Exemplares disponíveis ({l.exemplares_disponiveis}) > total ({l.exemplares_total})")
        if l.tipo_obra == 'BIBLIOGRAFIA' and not l.isbn:
            erros.append("Bibliografia sem ISBN")
            
        if erros:
            livros_invalidos.append((l, erros))
            
    print(f"Livros com inconsistências encontradas: {len(livros_invalidos)}")
    for l, erros in livros_invalidos:
        print(f"  - [Livro ID {l.pk}] '{l.titulo}' | Erros: {', '.join(erros)}")

    # 3. Auditoria de Empréstimos
    emprestimos = emprestimo.objects.all()
    emprestimos_invalidos = []
    print(f"\nAuditando {len(emprestimos)} empréstimos...")
    for e in emprestimos:
        erros = []
        if e.leitor.funcao != 'Leitor':
            erros.append(f"Leitor associado possui função '{e.leitor.funcao}' (deveria ser Leitor)")
            
        if erros:
            emprestimos_invalidos.append((e, erros))
            
    print(f"Empréstimos com inconsistências encontradas: {len(emprestimos_invalidos)}")
    for e, erros in emprestimos_invalidos:
        print(f"  - [Empréstimo ID {e.pk}] '{e.livro.titulo} -> {e.leitor.nome}' | Erros: {', '.join(erros)}")

    print("\n=== AUDITORIA CONCLUÍDA ===")

if __name__ == '__main__':
    run_audit()
