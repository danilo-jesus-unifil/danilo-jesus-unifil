# Guia de configuração

Este projeto é um painel de perfil para o repositório especial do GitHub. Ele consulta somente dados públicos do usuário `danilo-jesus-unifil`, gera quatro imagens SVG locais e as exibe no `README.md`. A análise de ecossistema percorre os repositórios públicos próprios, ignora forks e resume linguagens, tipos de arquivo, tamanho aproximado do código e famílias de arquivo.

## O que foi incluído

| Arquivo | Função |
| :--- | :--- |
| `.github/scripts/profile_update.py` | Consulta a API oficial e gera os cartões de métricas do perfil. |
| `.github/scripts/ecosystem_analysis.py` | Analisa linguagens, árvores Git e famílias de arquivos dos repositórios públicos próprios. |
| `.github/workflows/profile-update.yml` | Executa a atualização semanal dos cartões de perfil e publica mudanças reais. |
| `.github/workflows/ecosystem-analysis.yml` | Executa a atualização semanal do ecossistema e publica mudanças reais. |
| `assets/github-summary.svg` | Resumo de contribuições, commits, PRs, issues e repositórios. |
| `assets/github-languages.svg` | Principais linguagens dos repositórios públicos. |
| `assets/github-activity.svg` | Linha de atividade dos últimos 30 dias. |
| `assets/github-ecosystem.svg` | Linguagens, tipos de arquivo, arquivos totais e famílias do ecossistema público. |

## Primeira ativação

Abra o repositório `danilo-jesus-unifil/danilo-jesus-unifil` no GitHub e confirme que o branch padrão é `main`. Depois, abra **Settings → Actions → General → Workflow permissions** e selecione **Read and write permissions**. Essa permissão permite que o workflow atualize os SVGs no próprio repositório.

Em seguida, abra a aba **Actions**, execute manualmente **Atualizar painel do perfil** e **Atualizar análise do ecossistema** usando **Run workflow**. Depois de concluídas, volte ao perfil para confirmar que os quatro cartões aparecem no README.

O workflow usa `GITHUB_TOKEN`, um token temporário fornecido pelo próprio GitHub Actions. Não é necessário criar ou colar um token pessoal para o funcionamento normal com repositórios públicos.

## Teste local opcional

Para executar o mesmo gerador na máquina local, é necessário ter Python 3.11 ou superior e o GitHub CLI autenticado. O token não deve ser gravado em arquivo:

```bash
export GH_USER=danilo-jesus-unifil
GITHUB_TOKEN="$(gh auth token)" python3 .github/scripts/profile_update.py
GITHUB_TOKEN="$(gh auth token)" python3 .github/scripts/ecosystem_analysis.py
```

Depois, confira os arquivos alterados:

```bash
git status --short
python3 -m py_compile .github/scripts/profile_update.py .github/scripts/ecosystem_analysis.py
```

O script consulta apenas dados públicos e pode fazer várias chamadas à API porque a seção de linguagens precisa verificar os repositórios do usuário. Se o usuário tiver muitos repositórios, a atualização ainda é adequada para uma execução semanal, não horária.

## Frequência e commits

As duas atualizações estão programadas para uma vez por semana, aos domingos. Também é possível executá-las manualmente por `workflow_dispatch`. O analisador de ecossistema consulta a lista paginada de repositórios públicos próprios, o endpoint de linguagens e a árvore recursiva do branch padrão de cada repositório. Árvores com `truncated: true` e repositórios que falham são indicados no cartão e não interrompem necessariamente as demais análises.

Os scripts ignoram o carimbo de hora quando comparam os SVGs antigos com os novos. Assim, uma execução semanal sem alteração nas métricas termina sem criar commit. O projeto não monitora outros repositórios, não cria commits sem alteração e não gera atividade falsa.

## Personalizar o perfil

O texto do perfil deve ser editado diretamente no `README.md`. Para mudar o nome de usuário analisado, altere `USER` no script ou defina `GH_USER` no workflow. Como este repositório já corresponde ao perfil de Danilo, o valor padrão está configurado como `danilo-jesus-unifil`.

As cores e os títulos dos cartões ficam no início do `profile_update.py`. A alteração mais segura é editar as constantes de cor e os textos existentes, preservando as funções que escapam texto com `html.escape` e que comparam o conteúdo antes de escrever.

## Solução de problemas

| Problema | Solução |
| :--- | :--- |
| Os cartões não aparecem | Execute o workflow manualmente e confirme que os arquivos SVG foram publicados na pasta `assets/`. |
| O workflow não pode fazer push | Ative `Read and write permissions` nas configurações de Actions do repositório. |
| `GITHUB_TOKEN não encontrado` no teste local | Execute o comando com `GITHUB_TOKEN="$(gh auth token)"`. |
| Usuário não encontrado | Verifique `GH_USER` e confirme o nome exato da conta do GitHub. |
| A API respondeu com erro temporário | Aguarde alguns minutos e execute o workflow novamente; o GitHub pode aplicar limites de requisição. |
| O painel parece antigo | Verifique a data no rodapé do SVG e rode **Run workflow** manualmente. |

## Limitações intencionais

O painel mostra métricas da janela móvel de 365 dias fornecidas pelo GitHub. Ele não tenta reproduzir dados privados sem autorização, não monitora empresas ou organizações externas, não copia atividade de outros projetos e não promete atualização instantânea. Essa redução mantém o projeto simples, transparente e apropriado para um perfil pessoal.
