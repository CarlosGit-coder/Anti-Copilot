+++
title = "FastAPI: corpo de requisição com modelos Pydantic"
source_url = "https://fastapi.tiangolo.com/tutorial/body/"
organization = "FastAPI"
+++

# Corpo da requisição

O corpo é usado quando o cliente envia uma estrutura de dados para a API, algo comum em operações de criação ou atualização. No FastAPI, um modelo Pydantic declarado como parâmetro da função representa esse corpo. Os campos e tipos do modelo descrevem a entrada esperada.

FastAPI usa a declaração para interpretar o JSON, validar os valores e produzir documentação OpenAPI. Campos obrigatórios, opcionais e tipos incompatíveis aparecem no esquema e nas mensagens de erro. Um valor opcional costuma ter um valor padrão, como `None`, além de uma anotação que admite ausência.

## Combinar corpo, caminho e consulta

Uma função pode receber ao mesmo tempo um identificador do caminho, um modelo de corpo e parâmetros de consulta. O parâmetro cujo nome aparece no caminho vem da URL; um modelo Pydantic representa o corpo; tipos escalares que não aparecem no caminho são tratados como query parameters.

Quando o corpo não é reconhecido, verifique o `Content-Type`, o JSON enviado, o nome do parâmetro no endpoint e a estrutura dos campos do modelo. Um `GET` com corpo tem comportamento pouco interoperável; para enviar dados, a documentação orienta preferir métodos como POST, PUT, PATCH ou DELETE conforme a semântica da operação.
