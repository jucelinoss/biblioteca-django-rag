from django.contrib import admin
from .models import LivroEmbedding, RequisicaoIaLog


@admin.register(LivroEmbedding)
class LivroEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('livro', 'modelo_versao', 'dimensao', 'atualizado_em')
    list_filter = ('modelo_versao',)
    search_fields = ('livro__titulo', 'texto_fonte')
    readonly_fields = ('texto_fonte', 'modelo_versao', 'dimensao', 'atualizado_em')
    exclude = ('vetor',)  # esconde o blob


@admin.register(RequisicaoIaLog)
class RequisicaoIaLogAdmin(admin.ModelAdmin):
    list_display = ('tipo_servico', 'usuario', 'timestamp')
    list_filter = ('tipo_servico', 'timestamp')
    search_fields = ('usuario__username', 'entrada', 'saida')
    readonly_fields = ('tipo_servico', 'usuario', 'entrada', 'saida', 'timestamp')
