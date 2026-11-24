+++
title = "FastAPI: primeiros passos e operações de rota"
source_url = "https://fastapi.tiangolo.com/tutorial/first-steps/"
organization = "FastAPI"
+++

# Como uma aplicação FastAPI começa

Uma aplicação começa importando `FastAPI` e criando uma instância, normalmente chamada `app`. Essa instância registra as operações da API e é o ponto principal para configurar o serviço.

Uma operação de rota associa um caminho e um método HTTP a uma função Python. Por exemplo, `@app.get("/items")` define o que acontece quando chega uma requisição GET para `/items`. A função abaixo do decorador prepara o valor retornado.

## Métodos e caminhos

O caminho representa o recurso ou assunto exposto pela API, como `/items`. O método indica a ação: GET costuma consultar, POST costuma criar, PUT costuma substituir, PATCH costuma alterar parcialmente e DELETE costuma remover. A decisão deve acompanhar o significado da operação, e não apenas o nome da função.

O FastAPI constrói uma especificação OpenAPI a partir das rotas e declarações da aplicação. A especificação alimenta documentação interativa como Swagger UI em `/docs`, ReDoc em `/redoc` e o documento JSON em `/openapi.json`. Isso ajuda a inspecionar os contratos expostos sem escrever a documentação manualmente.

## Diagnóstico inicial

Se uma rota não aparece em `/docs`, confira se o módulo que declara a rota foi importado e se o `APIRouter` foi incluído na aplicação principal. Se a rota aparece mas responde com método não permitido, compare o método da requisição com o decorador registrado.
