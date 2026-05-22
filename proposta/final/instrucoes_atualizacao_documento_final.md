# Instruções para Atualizar o Documento Final

## Objetivo

Transformar `proposta_ufg_v7_final_png.md` de documento de prévia/proposta em relatório final da aplicação entregue. A revisão deve começar na Seção 5, mantendo a fundamentação teórica anterior praticamente intacta.

O tom geral deve passar de intenção futura para resultado realizado: "foi implementado", "desenvolvemos", "validamos", "entregamos", "a aplicação apresenta".

## Regra Geral de Revisão

- Não alterar a fundamentação teórica anterior à Seção 5, salvo correções pontuais de coerência.
- Trocar termos como `previsto`, `será`, `deve evoluir`, `recomendação é criar`, `planejado` por formulações de entrega concluída, quando a funcionalidade existir.
- Separar claramente três categorias:
  - Protótipo inicial: wireframes e propostas visuais.
  - Implementação final: telas, rotas, views, serviços e evidências da aplicação.
  - Trabalhos futuros: itens que não entraram na entrega final.
- Usar `/dashboard/` como rota final do painel analítico. Não usar `/metricas/` como rota principal no relatório final.

## 1. Seção 5 - Escopo do Sistema

### Trecho a alterar

Atual:

```text
Funcionalidades previstas
```

Substituir por:

```text
Funcionalidades desenvolvidas
```

### Ajustes recomendados

- Reescrever a lista em tom final, mantendo CRUD, autenticação, autorização, regras de empréstimo, relatório de atrasados e dashboards.
- Explicitar que a aplicação final ficou com duas superfícies de indicadores:
  - `/menu/`: dashboard operacional de entrada, com visão rápida do acervo e ações principais.
  - `/dashboard/`: painel analítico narrativo/storytelling, com capítulos de Acervo, Circulação, Leitores e IA.
- Onde o texto falar em "dashboard com contadores e indicadores básicos", complementar dizendo que a entrega final também inclui o painel analítico mais completo.
- Manter o diagrama de caso de uso como visão conceitual das permissões, atores e responsabilidades funcionais.
- Inserir os prints logo depois do diagrama, como evidências de como as funcionalidades aparecem hoje na interface da aplicação.

### Texto sugerido

```text
Na solução desenvolvida, foi desenvolvido o CRUD das entidades principais do domínio, autenticação com controle de acesso por grupos, regras de negócio para empréstimos e devoluções, relatório de atrasados e duas interfaces de acompanhamento: um dashboard operacional em /menu/ e um painel analítico narrativo em /dashboard/.
```

### Conexão entre diagrama e prints

Depois da lista de funcionalidades e antes do diagrama de caso de uso, usar uma frase de transição que deixe claro o papel de cada evidência: o diagrama explica o escopo funcional e os prints mostram a materialização atual da interface.

Texto sugerido:

```text
O diagrama de caso de uso sintetiza a visão funcional do módulo operacional, indicando os atores, permissões e principais responsabilidades do sistema. Em complemento, as capturas de tela apresentadas na sequência mostram como essas funcionalidades foram materializadas na interface atualmente implementada.
```

### Organização recomendada das figuras

Manter o diagrama de caso de uso como a primeira figura desta subseção:

```markdown
![Figura X - Diagrama de Caso de Uso](out/diagrama-casos-de-uso-biblioteca-v2/diagrama-casos-de-uso-biblioteca-v2.png)
```

Em seguida, inserir os prints na ordem abaixo.

Print 1, dashboard operacional:

```markdown
![Figura X - Dashboard operacional de entrada da aplicação](biblioteca-django-rag/docs/img/home.png)
```

Print 2, listagem do acervo:

```markdown
![Figura X - Listagem do acervo com paginação, busca e tipos de obra](biblioteca-django-rag/docs/img/consulta_livros.png)
```

Print 3, empréstimos e status:

```markdown
![Figura X - Consulta de empréstimos e status operacional](biblioteca-django-rag/docs/img/consulta_emprestimo.png)
```

### Fechamento sugerido para o parágrafo antes das figuras

Se quiser preservar o parágrafo atual que cita a Figura 2, substituir o trecho final por:

```text
Para sintetizar visualmente as permissões e responsabilidades do módulo operacional, a Figura 2 apresenta o diagrama de casos de uso. Na sequência, as Figuras 3, 4 e 5 mostram, respectivamente, o dashboard operacional, a listagem do acervo e a consulta de empréstimos, evidenciando como os casos de uso foram concretizados na interface.
```

## 2. Seção 5.2.1 - Recomendação por Similaridade Semântica

### Trecho a revisar

A subseção menciona "Personalização" para leitores com histórico. Essa capacidade existe no serviço backend, mas a interface demonstrável final está centrada na página de detalhe da obra, exibindo "Obras similares".

### Ajustes recomendados

- Dizer que a recomendação principal entregue na UI foi a recomendação entre obras.
- Manter MiniLM, HuggingFace, 384 dimensões, `BinaryField`, SQLite, `post_save` e top-5.
- Mencionar recomendação por perfil de leitor como capacidade preparada no backend, não como fluxo principal da interface final.
- Evitar dar a entender que existe uma tela "Para você" ou recomendação personalizada completa para o leitor, se ela não estiver implementada.

### Texto sugerido

```text
Na interface final, a recomendação semântica foi materializada principalmente na página de detalhe da obra. Ao acessar uma obra, o sistema calcula em tempo real as cinco obras semanticamente mais próximas, com base na similaridade cosseno entre embeddings gerados pelo modelo paraphrase-multilingual-MiniLM-L12-v2. A recomendação personalizada por histórico de leitor ficou preparada como serviço backend, mas não foi usada como fluxo principal de navegação nesta versão da aplicação.
```

### Imagem a inserir

```markdown
![Figura X - Detalhe da obra com recomendações semânticas](biblioteca-django-rag/docs/img/consulta_livro_recomendacao.png)
```

## 3. Seção 5.2.2 - Assistente Conversacional via RAG

### Trechos a alterar

Atual:

```text
O modelo escolhido como primeiro candidato é o llama-3.3-70b-versatile
```

Substituir por:

```text
O modelo utilizado na versão final foi o llama-3.3-70b-versatile
```

### Ajustes recomendados

- Trocar justificativas em tom de decisão por evidências de implementação.
- Reforçar que a tela final exibe:
  - resposta em linguagem natural;
  - citações no formato `(Obra #N)`;
  - cards clicáveis das obras citadas;
  - links para as páginas de detalhe das obras.
- Manter a estratégia de recuperação híbrida: acervo completo até 200 obras, fallback top-k acima desse limite.

### Texto sugerido

```text
Na versão final, o assistente conversacional foi integrado à rota /chat/. A pergunta do usuário é sanitizada, vetorizada com o mesmo MiniLM usado na recomendação semântica e enviada ao modelo generativo da Groq com contexto estruturado do acervo. A resposta é exibida em português, acompanhada de citações rastreáveis no formato (Obra #N) e de cards clicáveis das obras mencionadas.
```

### Imagem a inserir

```markdown
![Figura X - Assistente conversacional RAG com citação de fontes](biblioteca-django-rag/docs/img/chat_rag.png)
```

## 4. Seção 6.5 - Camada Analítica

### Trecho a alterar

Atual:

```text
A camada analítica foi implementada por meio de um painel na rota /dashboard, seguindo o protótipo apresentado na Figura 9. O painel será organizado em quatro blocos: Acervo, Circulação, Leitores e IA e Qualidade...
```

Substituir por:

```text
A camada analítica foi implementada por meio de um painel na rota /dashboard. O protótipo da Figura 9 serviu como referência conceitual inicial; na versão final, o painel foi entregue como uma tela de storytelling analítico, organizada em quatro capítulos: Acervo, Circulação, Leitores e IA.
```

### Ajustes recomendados

- Manter a Figura 9 como wireframe/protótipo inicial.
- Inserir a captura real final logo após a Figura 9.
- Trocar "A Figura 10 apresenta a modelagem proposta" por "A Figura 10 apresenta a modelagem analítica adotada".
- Trocar "Para o painel, a recomendação é criar 5 views SQL/read models" por "Para o painel, foram criadas 5 views SQL/read models".
- Corrigir referências a `/metricas/` para `/dashboard/`, quando o texto estiver falando da tela final.
- Não usar `metricas/templates/metricas/painel.html` como evidência principal; ele ficou como tela auxiliar/rascunho. A tela final está em `core/templates/core/metricas.html`.

### Texto sugerido

```text
O painel final preserva os quatro domínios do protótipo original, mas abandona a composição rígida em quadrantes. A aplicação organiza a análise como uma narrativa: primeiro apresenta KPIs de síntese e, em seguida, detalha cada capítulo com gráficos D3, notas interpretativas, rankings e listas curtas de ação.
```

### Imagem a inserir

Inserir logo depois da Figura 9:

```markdown
![Figura X - Painel analítico final em formato de storytelling](biblioteca-django-rag/docs/img/dashboard_storytelling.png)
```

## 5. Seção 7 - Segurança e Guardrails

### Trecho a alterar

Atual:

```text
Validação adversarial. O conjunto foi submetido a sete casos de teste adversariais...
```

Substituir por:

```text
Validamos a camada conversacional com sete cenários adversariais...
```

### Ajustes recomendados

- Manter as cinco camadas L1-L5.
- Reforçar que todos os sete cenários passaram.
- Informar que a recusa permaneceu em português brasileiro mesmo sob tentativa de troca de idioma.
- Manter o diagrama de guardrails atual.

### Texto sugerido

```text
Validamos a camada conversacional com sete cenários adversariais, cobrindo pergunta legítima, tema fora de escopo, injeção clássica de instruções, jailbreak de persona, troca de idioma, pedido de revelação do prompt e pergunta sensível de saúde. Em todos os casos, o comportamento observado foi compatível com o esperado: resposta útil quando a pergunta estava no escopo, recusa padronizada nos casos indevidos, preservação do português brasileiro e ausência de citações indevidas.
```

## 6. Seção 8 - Metodologia

### Trechos a alterar

Atual:

```text
O backlog é mantido...
```

Substituir por:

```text
O backlog foi mantido...
```

Atual:

```text
A documentação técnica é construída...
```

Substituir por:

```text
A documentação técnica foi construída...
```

### Ajustes recomendados

- Remover ou mover para "trabalhos futuros" a frase sobre "Novos testes de view e de pipeline RAG estão planejados...".
- Mencionar como artefatos de entrega:
  - `README.md`;
  - `CHANGELOG.md`;
  - ADR do modelo de embeddings;
  - documentação de segurança do chat;
  - métricas;
  - roteiro de demonstração.
- Evitar citar como evidência final documentos ainda incompletos, especialmente `docs/avaliacao_qualitativa.md`.

### Texto sugerido

```text
A documentação técnica foi construída em paralelo ao código e consolidada em artefatos de entrega, incluindo README executável, CHANGELOG versionado, ADR do modelo de embeddings, relatório de segurança do chat, registros de métricas e roteiro de demonstração da apresentação final.
```

## 7. Seção 9 - Ferramentas Utilizadas

### Ajustes recomendados

- Manter Python, Django 4.2, SQLite, Bootstrap 5, django-bootstrap-v5, django-tables2, HuggingFace, Groq, numpy, Git, pytest/django.test, ruff e black.
- Acrescentar D3.js como biblioteca usada nos gráficos do painel analítico/storytelling.
- Acrescentar `python-dotenv` para carregamento das variáveis de ambiente via `.env`.
- Citar Plotly apenas como apoio/experimento, se necessário; não tratá-lo como base do painel final.

### Texto sugerido

```text
- Visualização analítica: D3.js, utilizado no painel /dashboard/ para renderizar gráficos interativos de acervo, circulação, leitores e cobertura de IA.

- Configuração de ambiente: python-dotenv, usado para carregar chaves e configurações sensíveis a partir de arquivo .env ignorado pelo controle de versão.
```

## 8. Seção 10 - Cronograma

### Trecho a alterar

Atual:

```text
O trabalho está organizado em quatro sprints, totalizando aproximadamente sete semanas de execução, com entrega final prevista para 06 de junho de 2026.
```

Substituir por:

```text
O trabalho foi executado em quatro sprints, totalizando aproximadamente sete semanas de desenvolvimento e culminando na entrega final em 06 de junho de 2026.
```

### Ajustes recomendados

- Transformar a seção em retrospectiva.
- Manter a tabela, mas escrever as entregas como concluídas.
- Em Sprint 3, destacar "painel analítico/storytelling, documentação final e apresentação".

### Texto sugerido para Sprint 3

```text
Refinamentos finais, painel analítico em formato de storytelling, documentação final, roteiro de demonstração e preparação da apresentação.
```

## 9. Seção 12 - Resultados

### Trechos a alterar

Atual:

```text
RESULTADOS ESPERADOS
```

Substituir por:

```text
RESULTADOS OBTIDOS
```

Atual:

```text
Ao final da disciplina, o grupo entregou um conjunto de artefatos que demonstrem...
```

Substituir por:

```text
Ao final da disciplina, o grupo entregou um conjunto de artefatos que demonstram...
```

### Ajustes recomendados

- Remover da lista principal:

```text
Migração para um banco vetorial caso a aplicação passe a gerenciar mais de 10 mil obras
```

- Criar uma subseção curta chamada `Trabalhos futuros` com:
  - migração para PostgreSQL/pgvector caso o acervo cresça;
  - logging persistente de perguntas;
  - rate limiting;
  - histórico de conversa;
  - feedback de recomendações.

### Correções pontuais

Atual:

```text
A execution deste trabalho
```

Substituir por:

```text
A execução deste trabalho
```

### Texto sugerido para trabalhos futuros

```text
Como evolução futura, a aplicação pode migrar de SQLite para PostgreSQL com pgvector em cenários de acervo maior, persistir logs de perguntas para auditoria, adicionar rate limiting para proteção da API generativa, manter histórico de conversa por sessão e incorporar feedback explícito dos usuários nas recomendações.
```

## Fontes Internas Recomendadas

Usar como evidência principal:

- `biblioteca-django-rag/README.md`
- `biblioteca-django-rag/CHANGELOG.md`
- `biblioteca-django-rag/docs/demo_script.md`
- `biblioteca-django-rag/docs/seguranca_chat.md`
- `biblioteca-django-rag/core/analytics.py`
- `biblioteca-django-rag/core/templates/core/metricas.html`
- `biblioteca-django-rag/core/migrations/0003_analytics_views.py`
- `biblioteca-django-rag/core/migrations/0004_fix_analytics_date_formats.py`

Usar com cuidado:

- `biblioteca-django-rag/docs/mvp_features.md`, pois ainda contém trechos antigos dizendo que analytics era proposta.
- `biblioteca-django-rag/docs/metricas_sprint1.md`, pois a seção de dashboard ainda fala como Sprint 3 futura.
- `biblioteca-django-rag/docs/avaliacao_qualitativa.md`, pois ainda está marcado como "a preencher".

## Checklist de Verificação

Depois de aplicar as alterações no relatório final:

- Procurar por `previstas`, `será`, `deve evoluir`, `recomendação é criar`, `planejado`, `resultados esperados`.
- Confirmar que as imagens abaixo existem e estão referenciadas corretamente:
  - `biblioteca-django-rag/docs/img/home.png`
  - `biblioteca-django-rag/docs/img/consulta_livros.png`
  - `biblioteca-django-rag/docs/img/consulta_emprestimo.png`
  - `biblioteca-django-rag/docs/img/consulta_livro_recomendacao.png`
  - `biblioteca-django-rag/docs/img/chat_rag.png`
  - `biblioteca-django-rag/docs/img/dashboard_storytelling.png`
- Confirmar que a rota final do painel analítico aparece como `/dashboard/`.
- Confirmar que o texto diferencia protótipo inicial, implementação final e trabalhos futuros.
- Confirmar que "RESULTADOS ESPERADOS" foi renomeado para "RESULTADOS OBTIDOS".
- Confirmar que "A execution deste trabalho" foi corrigido para "A execução deste trabalho".
