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


class LivroSerializer(serializers.ModelSerializer):
    class Meta:
        model = livro
        fields = ['id', 'titulo', 'autor', 'tipo_obra', 'isbn', 'ano', 'exemplares_total', 'exemplares_disponiveis']

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
        # Validações extras para criação de novos empréstimos
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
