+++
title = "FastAPI: segurança e OAuth2"
source_url = "https://fastapi.tiangolo.com/tutorial/security/"
organization = "FastAPI"
+++

# Segurança como dependência

Os mecanismos de segurança do FastAPI se integram ao sistema de dependências. Uma rota declara as credenciais ou o usuário de que precisa; a dependência extrai e valida esses dados antes de executar a operação.

O fluxo de tutorial OAuth2 com senha e bearer token separa autenticação e acesso à rota protegida. O cliente envia credenciais ao endpoint de token e recebe um token para usar em requisições seguintes. Uma dependência de usuário atual interpreta a autorização e pode impedir a execução quando a credencial não é válida.

## Senha e token são coisas diferentes

O token é apresentado nas chamadas protegidas e não deve ser tratado como a senha original. A aplicação deve armazenar senhas com hash adequado, comparar o hash no login e proteger segredos de assinatura por configuração segura. Um exemplo didático não substitui revisão das práticas de segurança antes de uso real.

## Diagnóstico de 401 e 403

Para uma resposta 401, inspecione se o cliente enviou o cabeçalho Authorization com o esquema e token esperados e se a dependência conseguiu validá-lo. Para 403, revise as regras de autorização e permissões depois da identificação do usuário. Consulte a documentação para distinguir o fluxo simples do tutorial de uma implantação completa com provedores externos.
