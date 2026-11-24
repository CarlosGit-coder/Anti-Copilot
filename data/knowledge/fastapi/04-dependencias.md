+++
title = "FastAPI: sistema de dependências"
source_url = "https://fastapi.tiangolo.com/tutorial/dependencies/"
organization = "FastAPI"
+++

# Injeção de dependências

Uma dependência é uma função ou classe cujo resultado FastAPI calcula e fornece a uma operação de rota. Ela é declarada com `Depends`. O endpoint declara o que precisa; a dependência reúne a lógica reutilizável para obter ou validar esse valor.

Casos comuns incluem extrair parâmetros compartilhados, validar um usuário autenticado, abrir recursos para uma requisição e fornecer configurações. Dependências podem usar outras dependências, formando uma árvore que o framework resolve antes de chamar a rota.

## Dependências com recursos

Uma dependência com `yield` pode executar preparação antes de entregar um recurso e finalização depois que o uso termina. Isso é útil para recursos de duração limitada, como uma sessão de banco. A limpeza precisa ficar na parte de finalização para que aconteça mesmo quando o endpoint falha.

Dependências globais podem ser configuradas na aplicação ou em um roteador e executadas para todas as rotas daquele escopo. Antes de adicionar uma verificação global, confirme se ela deve realmente valer para cada operação e se existe uma exceção explícita.

## Diagnóstico

Se um valor esperado não chega à rota, confira o tipo declarado e de onde FastAPI interpreta cada parâmetro. Verifique também se a dependência foi passada com `Depends`, se as dependências aninhadas têm os valores necessários e se uma dependência global está sendo aplicada ao roteador correto.
