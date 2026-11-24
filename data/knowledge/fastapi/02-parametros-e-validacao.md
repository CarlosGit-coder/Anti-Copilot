+++
title = "FastAPI: parâmetros de rota, query e validação"
source_url = "https://fastapi.tiangolo.com/tutorial/path-params/"
organization = "FastAPI"
+++

# Parâmetros de caminho

Um parâmetro pode ser declarado no caminho com chaves, como `/items/{item_id}`. O nome entre chaves precisa corresponder a um argumento da função da rota. FastAPI extrai o valor da URL e o entrega à função.

Anotações de tipo Python descrevem o tipo esperado. Com `item_id: int`, uma parte numérica da URL é convertida para inteiro; uma entrada incompatível recebe uma resposta de validação com detalhes do campo. As anotações também ajudam o editor e são usadas para compor o esquema OpenAPI.

## Ordem de rotas

Rotas fixas devem ser declaradas antes de rotas parametrizadas que poderiam capturar o mesmo caminho. Por exemplo, `/users/me` precisa ser registrada antes de `/users/{user_id}` para que `me` não seja tratado como identificador variável.

## Parâmetros de consulta

Valores que não fazem parte do caminho podem ser recebidos como parâmetros de consulta, por exemplo `?skip=0&limit=20`. Argumentos da função que não aparecem no caminho e não são modelos de corpo são normalmente interpretados como query parameters. Valores padrão os tornam opcionais; anotações especificam o tipo e permitem validação.

Quando um parâmetro recebe dados inválidos, a resposta de validação ajuda a localizar o valor rejeitado e o motivo. Para investigar, compare o nome e o tipo declarado no endpoint com o formato real enviado pelo cliente.
