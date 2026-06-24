import os
import sys
import django

# Setup Django (adjusted for subfolder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblioteca_mvp.settings')
django.setup()

from core.models import livro

def calcular_digito_verificador_isbn13(prefixo12: str) -> str:
    """Calcula o dígito verificador oficial do padrão ISBN-13."""
    soma = 0
    for idx, char in enumerate(prefixo12):
        digito = int(char)
        peso = 3 if idx % 2 == 1 else 1
        soma += digito * peso
    resto = soma % 10
    digito_v = 10 - resto if resto != 0 else 0
    return str(digito_v)

def validar_isbn(value: str) -> tuple[bool, str]:
    """Valida se o ISBN atende às regras do Serializer da API (10 ou 13 dígitos numéricos)."""
    if not value:
        return False, "Ausente"
    val = value.replace("-", "").replace(" ", "")
    if len(val) not in (10, 13):
        return False, f"Tamanho inválido ({len(val)} dígitos)"
    if not val.isdigit() and not (len(val) == 10 and val[:-1].isdigit() and val[-1].upper() == 'X'):
        return False, "Caracteres inválidos (apenas números são permitidos)"
    return True, "Válido"

def run():
    print("=== SCRIPT DE VALIDAÇÃO E CORREÇÃO DE ISBNS ===")
    livros = livro.objects.all()
    print(f"Total de livros no banco: {len(livros)}")
    
    invalidos = []
    for l in livros:
        if l.tipo_obra == 'BIBLIOGRAFIA':
            valido, motivo = validar_isbn(l.isbn)
            if not valido:
                invalidos.append((l, motivo))
                
    print(f"\nObras do tipo BIBLIOGRAFIA com ISBN inválido: {len(invalidos)}")
    for l, motivo in invalidos:
        print(f"  - [ID {l.pk}] '{l.titulo}' | Autor: {l.autor} | ISBN Atual: {l.isbn} | Motivo: {motivo}")
        
    if not invalidos:
        print("\n[OK] Nenhum livro com ISBN inválido encontrado na base de dados.")
        return
        
    corrigir = '--fix' in sys.argv
    if not corrigir:
        print("\nPara corrigir esses registros automaticamente com ISBNs fictícios válidos de 13 dígitos,")
        print("execute este script passando a flag '--fix':")
        print("  python validar_corrigir_isbns.py --fix")
        return
        
    print("\nExecutando correção automática...")
    corrigidos = 0
    for idx, (l, _) in enumerate(invalidos, start=1):
        # Cria um prefixo exclusivo de 12 dígitos iniciado com 978999
        # ex: 978999000001, 978999000002...
        sequencial = f"999{idx:06d}"
        prefixo12 = f"978{sequencial}"
        digito_v = calcular_digito_verificador_isbn13(prefixo12)
        novo_isbn = f"{prefixo12}{digito_v}"
        
        # Validação cruzada antes de salvar
        valido, _ = validar_isbn(novo_isbn)
        if valido:
            old_isbn = l.isbn
            l.isbn = novo_isbn
            l.save()
            print(f"  [ID {l.pk}] '{l.titulo}' corrigido de '{old_isbn}' para '{novo_isbn}'")
            corrigidos += 1
        else:
            print(f"  Erro ao gerar ISBN válido para [ID {l.pk}]")
            
    print(f"\n=== CORREÇÃO CONCLUÍDA: {corrigidos} de {len(invalidos)} livros corrigidos com sucesso! ===")

if __name__ == '__main__':
    run()
