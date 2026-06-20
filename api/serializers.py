import re
from rest_framework import serializers
from core.models import pessoa, livro, emprestimo


class PessoaSerializer(serializers.ModelSerializer):
    class Meta:
        model = pessoa
        fields = ['id', 'nome', 'email', 'celular', 'funcao', 'nascimento', 'ativo']

    def validate_funcao(self, value):
        if value not in ['Leitor', 'Bibliotecario']:
            raise serializers.ValidationError("A funcao deve ser 'Leitor' ou 'Bibliotecario'.")
        return value

    def validate_celular(self, value):
        if value:
            # Validação simples de celular BR: +55 (11) 91234-5678, ou apenas digitos
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 11:
                raise serializers.ValidationError("Celular deve conter 10 ou 11 dígitos.")
        return value


class LivroSerializer(serializers.ModelSerializer):
    class Meta:
        model = livro
        fields = ['id', 'titulo', 'autor', 'tipo_obra', 'isbn', 'ano', 'exemplares_total', 'exemplares_disponiveis']

    def validate_isbn(self, value):
        if value:
            # Valida ISBN-10 ou ISBN-13 basico
            val = value.replace("-", "").replace(" ", "")
            if len(val) not in (10, 13):
                raise serializers.ValidationError("O ISBN deve ter 10 ou 13 caracteres numéricos.")
            if not val.isdigit() and not (len(val) == 10 and val[:-1].isdigit() and val[-1].upper() == 'X'):
                raise serializers.ValidationError("Formato de ISBN inválido.")
        return value

    def validate(self, attrs):
        tipo_obra = attrs.get('tipo_obra', getattr(self.instance, 'tipo_obra', None))
        isbn = attrs.get('isbn', getattr(self.instance, 'isbn', None))
        exemplares_total = attrs.get('exemplares_total', getattr(self.instance, 'exemplares_total', 1))
        exemplares_disponiveis = attrs.get('exemplares_disponiveis', getattr(self.instance, 'exemplares_disponiveis', 1))

        if tipo_obra == 'BIBLIOGRAFIA' and not isbn:
            raise serializers.ValidationError({"isbn": "ISBN e obrigatorio para Bibliografia."})

        if exemplares_disponiveis > exemplares_total:
            raise serializers.ValidationError({"exemplares_disponiveis": "Exemplares disponiveis nao pode ser maior que total."})

        return attrs


class EmprestimoSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()
    atrasado = serializers.ReadOnlyField()

    class Meta:
        model = emprestimo
        fields = ['id', 'livro', 'leitor', 'data_saida', 'data_devolucao_prevista', 'data_devolucao_real', 'status', 'atrasado']
        read_only_fields = ['data_saida', 'data_devolucao_prevista']

    def validate(self, attrs):
        # Valizações extras para criação de novos empréstimos
        if not self.instance:
            livro_obj = attrs.get('livro')
            leitor_obj = attrs.get('leitor')
            
            if livro_obj and livro_obj.exemplares_disponiveis <= 0:
                raise serializers.ValidationError({"livro": f'Obra "{livro_obj.titulo}" nao tem exemplares disponiveis.'})
            if leitor_obj and not leitor_obj.ativo:
                raise serializers.ValidationError({"leitor": f'Leitor "{leitor_obj.nome}" esta inativo.'})
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['livro_detalhe'] = {
            'id': instance.livro.id,
            'titulo': instance.livro.titulo,
            'autor': instance.livro.autor
        }
        rep['leitor_detalhe'] = {
            'id': instance.leitor.id,
            'nome': instance.leitor.nome,
            'email': instance.leitor.email
        }
        return rep


class RecomendacaoIASerializer(serializers.Serializer):
    livro_id = serializers.IntegerField(required=True)
    quantidade = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)


class ChatIASerializer(serializers.Serializer):
    pergunta = serializers.CharField(
        required=True,
        max_length=1000,
        error_messages={
            'max_length': 'A pergunta excede o limite máximo de 1000 caracteres no prompt de IA.',
            'blank': 'A pergunta não pode estar vazia.'
        }
    )

    def validate_pergunta(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("A pergunta deve ter pelo menos 3 caracteres.")
        return value


class LivroMinimalSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID do livro")
    titulo = serializers.CharField(help_text="Título do livro")


class RecomendacaoResponseSerializer(serializers.Serializer):
    class RecomendadoSerializer(serializers.Serializer):
        id = serializers.IntegerField(help_text="ID do livro recomendado")
        titulo = serializers.CharField(help_text="Título do livro recomendado")
        autor = serializers.CharField(help_text="Autor do livro recomendado")
        score_similaridade = serializers.FloatField(help_text="Score de similaridade cosseno (0.0 a 1.0)")

    livro_origem = LivroMinimalSerializer(help_text="Livro que serviu como base para a recomendação")
    recomendacoes = RecomendadoSerializer(many=True, help_text="Lista de obras sugeridas por proximidade semântica")


class ChatResponseSerializer(serializers.Serializer):
    pergunta = serializers.CharField(help_text="Pergunta feita pelo usuário")
    resposta = serializers.CharField(help_text="Resposta contextualizada gerada pela IA (RAG)")
    obras_citadas = LivroMinimalSerializer(many=True, help_text="Lista de obras do acervo que sustentam a resposta")
    timestamp = serializers.DateTimeField(help_text="Momento em que a resposta foi processada")
