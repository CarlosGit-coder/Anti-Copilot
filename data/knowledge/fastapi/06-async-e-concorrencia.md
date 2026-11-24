+++
title = "FastAPI: async, def e operações bloqueantes"
source_url = "https://fastapi.tiangolo.com/async/"
organization = "FastAPI"
+++

# Quando usar async def

`async def` permite aguardar operações de entrada e saída que oferecem suporte a `await`, como chamadas assíncronas de rede. Enquanto uma operação espera, o servidor pode avançar outras requisições. Essa característica ajuda sobretudo quando o trabalho é aguardar I/O.

Funções síncronas declaradas com `def` também são aceitas para operações e dependências. O framework trata esses casos de maneira apropriada; é possível misturar funções síncronas e assíncronas no mesmo projeto. Quando uma biblioteca usada é síncrona, chamá-la diretamente dentro de `async def` pode bloquear o loop durante a chamada.

## I/O não é o mesmo que CPU

Esperar banco, rede ou disco é um caso de I/O. Cálculos intensivos, processamento de imagem e operações grandes de machine learning consomem CPU. Tornar uma função `async` não paraleliza automaticamente cálculos de CPU nem torna uma biblioteca bloqueante assíncrona.

## Diagnóstico de lentidão

Ao investigar uma rota lenta, identifique primeiro se o tempo é gasto esperando I/O ou executando cálculo. Confira se as bibliotecas chamadas oferecem API assíncrona. Se não oferecem, avalie executar a chamada síncrona em um caminho apropriado ou usar uma estratégia de trabalho separada, conforme a necessidade. Não adicione `async` sem identificar o tipo de espera.
