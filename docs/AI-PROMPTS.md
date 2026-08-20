# Pacote de prompts para o painel do GitHub

Este arquivo contém prompts prontos para usar com ChatGPT, Claude, Copilot ou outra IA de programação. Eles foram escritos para este repositório e já informam a estrutura, o objetivo e as restrições do projeto.

> Regra principal: o painel deve refletir atividade real do GitHub. Não peça à IA para criar commits artificiais, manipular contadores ou simular contribuições.

## 1. Prompt para entender o projeto

```text
Você está trabalhando no repositório especial de perfil do GitHub `danilo-jesus-unifil/danilo-jesus-unifil`.

O projeto possui:
- `README.md`, que exibe três SVGs locais da pasta `assets/`;
- `.github/scripts/profile_update.py`, que consulta a API oficial do GitHub e gera os cartões;
- `.github/workflows/profile-update.yml`, que roda semanalmente e publica somente mudanças reais;
- `docs/SETUP.md`, com a configuração operacional.

O objetivo é manter um perfil visual simples e profissional com:
1. resumo de contribuições, commits, pull requests, issues e repositórios públicos;
2. principais linguagens dos repositórios públicos;
3. gráfico de atividade dos últimos 30 dias.

Antes de alterar qualquer arquivo, leia o README, o script, o workflow e o guia de setup. Explique o que cada parte faz, quais arquivos serão alterados e como você vai evitar commits artificiais, chamadas desnecessárias e dependências externas.
```

## 2. Prompt para criar o painel do zero

```text
Crie um painel de perfil para o repositório especial `danilo-jesus-unifil/danilo-jesus-unifil`.

Requisitos obrigatórios:
- Use Python padrão, sem dependências externas instaladas por pip.
- Consulte somente a API oficial do GitHub.
- Use GraphQL para as métricas de contribuições dos últimos 365 dias.
- Use a API REST para listar repositórios públicos sem forks e consultar linguagens.
- Gere SVGs locais e acessíveis em `assets/`.
- Mostre um cartão de resumo, um cartão de linguagens e um gráfico dos últimos 30 dias.
- Use tema escuro com detalhes dourados, texto legível e `html.escape` para qualquer texto vindo da API.
- Use `GH_USER` como variável de ambiente, com padrão `danilo-jesus-unifil`.
- Use `GITHUB_TOKEN` no workflow; nunca grave tokens no código ou no README.
- Crie um workflow semanal com `workflow_dispatch` para execução manual.
- Dê ao job apenas `contents: write` e faça commit somente se os SVGs mudarem.
- Ignore o carimbo de hora ao comparar os arquivos para não criar um commit semanal quando os números forem iguais.
- Não implemente monitor de outros repositórios, contador de commits, gerador de atividade, streak artificial ou qualquer mecanismo de manipulação de métricas.

Crie ou atualize `README.md`, `.github/scripts/profile_update.py`, `.github/workflows/profile-update.yml`, `docs/SETUP.md` e `docs/AI-PROMPTS.md`. Depois, rode `python3 -m py_compile .github/scripts/profile_update.py` e descreva os testes feitos.
```

## 3. Prompt para personalizar o texto e o visual

```text
Personalize este painel do GitHub sem mudar sua arquitetura.

Repositório: `danilo-jesus-unifil/danilo-jesus-unifil`.

Faça estas alterações:
- Nome exibido: [INFORME O NOME]
- Descrição curta: [INFORME A DESCRIÇÃO]
- Tecnologias de interesse: [INFORME AS TECNOLOGIAS]
- Projetos em destaque: [INFORME OS PROJETOS]
- Links de contato: [INFORME OS LINKS]
- Cor principal: [INFORME A COR HEX, se quiser mudar]

Edite o texto do `README.md` e, se necessário, os títulos dos SVGs no `profile_update.py`. Preserve as métricas reais, a sanitização de HTML, o uso de `GITHUB_TOKEN` e a regra de não criar commits quando os dados não mudaram. Não adicione serviços externos de cartões. Mostre um diff resumido e valide a sintaxe do Python e do YAML.
```

## 4. Prompt para adicionar uma métrica oficial

```text
Adicione ao painel uma nova métrica oficial disponível na API do GitHub.

Métrica desejada: [NOME DA MÉTRICA]
Fonte oficial esperada: [CAMPO DA API, se souber]
Cartão de destino: [RESUMO / LINGUAGENS / ATIVIDADE]

Antes de editar:
1. Confirme se o campo realmente existe na API usada pelo projeto.
2. Verifique se a métrica pertence à janela de 365 dias ou é um total atual.
3. Atualize a consulta, o dicionário de dados e o SVG de maneira consistente.
4. Atualize `docs/SETUP.md` e este pacote de prompts se o comportamento operacional mudar.
5. Não substitua dados oficiais por estimativas e não crie um contador local que pareça ser uma contribuição do GitHub.

Depois de editar, rode `python3 -m py_compile .github/scripts/profile_update.py`, gere os SVGs com um token local temporário e confira se os números e rótulos estão coerentes.
```

## 5. Prompt para corrigir falha do workflow

```text
Investigue uma falha no workflow `Atualizar painel do perfil` deste repositório.

Mensagem de erro:
[COLE A MENSAGEM COMPLETA AQUI]

Siga esta ordem:
1. Leia `.github/workflows/profile-update.yml` e `.github/scripts/profile_update.py`.
2. Verifique se `permissions: contents: write` está presente.
3. Verifique se o job usa `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` e `GH_USER: ${{ github.repository_owner }}`.
4. Verifique se o branch usado pelo workflow é `main`.
5. Verifique se os caminhos adicionados ao `git add` existem.
6. Verifique se a comparação estável impede commits quando apenas a hora mudou.
7. Corrija somente a causa necessária, sem criar tokens pessoais no repositório.

No final, mostre os arquivos alterados, explique a causa e rode os testes de sintaxe.
```

## 6. Prompt para atualizar manualmente os cartões

```text
Atualize os cartões do perfil `danilo-jesus-unifil` localmente.

Use o script já existente, sem reescrevê-lo:

export GH_USER=danilo-jesus-unifil
GITHUB_TOKEN="$(gh auth token)" python3 .github/scripts/profile_update.py

Depois:
- execute `git status --short`;
- confira se existem `assets/github-summary.svg`, `assets/github-languages.svg` e `assets/github-activity.svg`;
- não faça commit automático;
- se houver alterações, explique quais dados mudaram antes de eu decidir se quero publicar.
```

## 7. Prompt para revisão de segurança e privacidade

```text
Faça uma revisão de segurança e privacidade deste painel de perfil.

Verifique especificamente:
- se algum token, segredo ou cookie aparece no código, no README, nos logs ou nos SVGs;
- se os textos obtidos da API passam por escape antes de serem inseridos no SVG;
- se o workflow tem permissões maiores do que `contents: write`;
- se o projeto tenta acessar repositórios privados sem uma necessidade explícita;
- se os nomes e links gerados apontam somente para o usuário configurado;
- se uma falha em um repositório impede a atualização inteira sem uma mensagem clara;
- se existe qualquer lógica para fabricar atividade, commits, contribuições ou streaks.

Não faça alterações destrutivas. Entregue uma tabela com risco, evidência, correção recomendada e prioridade. Se encontrar um segredo real, não o repita; apenas informe o caminho e recomende sua revogação.
```

## 8. Prompt para revisão antes de publicar

```text
Revise as alterações deste repositório antes do push.

Critérios:
- `README.md` exibe os três SVGs com caminhos relativos corretos;
- os três SVGs são válidos e não contêm scripts ou links inesperados;
- `profile_update.py` compila com Python 3.11+;
- o workflow tem gatilhos semanal, manual e de mudança no código;
- o workflow não entra em loop quando o bot atualiza apenas os SVGs;
- o commit só ocorre depois de `git diff --cached --quiet` indicar mudança real;
- o texto deixa claro que não há milhares de commits artificiais;
- a documentação explica como ativar permissões de escrita e como testar localmente;
- nenhuma credencial está sendo versionada.

Use `git diff --check`, `python3 -m py_compile .github/scripts/profile_update.py` e uma verificação de links locais. Não faça push; apenas entregue o relatório e aguarde confirmação.
```

## Como usar este arquivo

Para uma mudança comum, comece pelo prompt 1, use o prompt específico da alteração e finalize com o prompt 8. Para corrigir um workflow quebrado, use diretamente o prompt 5 e depois o prompt 7. Sempre forneça à IA a mensagem de erro completa e peça que ela leia os arquivos existentes antes de reescrever qualquer coisa.

## Referências

[1]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication "GitHub Docs — Automatic token authentication"
[2]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows "GitHub Docs — Events that trigger workflows"
