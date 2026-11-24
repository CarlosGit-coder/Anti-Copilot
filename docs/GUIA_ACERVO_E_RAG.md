# Guia do acervo, da ingestão e do RAG

Este guia acompanha a implementação do Anti-Copilot. A meta é deixar você capaz de explicar e ampliar a base: de onde veio cada trecho, como ele virou vetor e como a busca escolhe o contexto para a resposta.

## 1. O fluxo completo

```text
sources.toml ──define──> arquivos locais autorizados
                              │
data/raw/ ──extrai texto──> páginas/seções
                              │
                        divide em chunks
                              │
                 E5 gera vetores normalizados
                              │
                 Chroma guarda vetor + texto + origem
                              │
pergunta ──prefixo query: ──> busca cosine ──> RAG/Gemini
```

Cada parte tem uma responsabilidade separada:

| Arquivo | Responsabilidade |
| --- | --- |
| `data/catalog/sources.toml` | Catálogo legível por pessoas: autoria, endereço, licença, pasta local e padrões de arquivos. |
| `src/anti_copilot/catalog.py` | Lê o TOML e recusa IDs duplicados, campos ausentes, URLs inválidas e regras de ingestão incompletas. |
| `src/anti_copilot/ingestion.py` | Descobre arquivos autorizados, extrai PDF/texto/código, divide o conteúdo e cria metadados de proveniência. |
| `src/anti_copilot/embeddings.py` | Calcula vetores com `intfloat/multilingual-e5-small`, localmente. |
| `src/anti_copilot/rag.py` | Grava e consulta vetores, texto e metadados em uma coleção persistente Chroma. |
| `src/anti_copilot/knowledge_cli.py` | Expõe comandos para listar fontes, ingerir documentos e inspecionar resultados recuperados. |
| `src/anti_copilot/assistant.py` | Recupera os trechos mais próximos e os envia como contexto ao modelo de conversa. |
| `src/anti_copilot/app.py` | Interface Streamlit, contagem SOS, confirmação, Mermaid e relatório. Usa o banco já indexado; não faz ingestão escondida. |

## 2. Onde ficam as coisas

```text
data/
├── catalog/
│   └── sources.toml       # metadados e regras do acervo
├── raw/
│   ├── google_engineering_practices/
│   │   └── standard.md    # cópia original com licença e URL no catálogo
│   ├── books/             # PDFs abertos de Think Java e Think Python
│   └── repositories/      # clones locais; ignorados pelo Git
└── chroma/                # banco vetorial persistente; gerado localmente
```

`raw` preserva o material de origem. O código de ingestão não modifica os arquivos originais. `chroma` é uma saída gerada: pode ser recriada a partir do catálogo e dos documentos locais.

## 3. O catálogo TOML

Cada bloco `[[sources]]` representa uma fonte. `id` é um identificador estável usado nos metadados do Chroma; mantenha-o único. `url` aponta para a origem pública. `local_path` diz onde está a cópia ou checkout local. `include` lista padrões de arquivos relativos a essa pasta. `exclude` remove caminhos específicos. `topics` ajuda a identificar o conteúdo; o pipeline salva a lista em JSON dentro dos metadados porque os valores de metadados do Chroma devem ser escalares.

`ingestion` controla a entrada automática:

- `allowed_with_attribution`: a ingestão é permitida, e o catálogo precisa registrar licença, URL da licença, pasta local e padrões de arquivos.
- `review_terms`: a fonte está catalogada, mas o pipeline não a indexa até os termos serem verificados.
- `metadata_only_until_terms_review`: mantém a referência bibliográfica sem indexar o conteúdo.

O CLI só processa fontes `allowed_with_attribution`. Essa condição é uma proteção operacional; ela não substitui a leitura da licença ou dos termos do material.

### Campos que viram metadados em cada chunk

`source_id`, título, organização, URL, licença, revisão do repositório, arquivo, SHA-256 do arquivo, idioma, tópicos, número da página, seção, índice do chunk e `context_global` acompanham cada trecho. Assim, a busca pode mostrar a origem e a página, e filtros futuros podem limitar a busca por fonte, idioma, tópico ou tipo de material.

`context_global` inclui título, organização, caminho e revisão. Ele é incorporado ao texto usado para calcular o embedding e também fica salvo como metadado. Isso reduz o isolamento de uma função ou classe removida do contexto geral do arquivo.

## 4. Como adicionar um PDF

1. Confira se os termos permitem usar o documento como parte da base e registrar sua atribuição. Livros comerciais permanecem como `metadata_only_until_terms_review` até isso estar claro.
2. Crie uma pasta com o mesmo ID da fonte dentro de `data/raw/` e coloque nela o PDF. Por padrão, PDFs são ignorados pelo Git para não publicar um livro ou material privado sem querer.
3. Acrescente uma entrada ao catálogo. Exemplo estrutural:

   ```toml
   [[sources]]
   id = "guia_de_arquitetura_aberta"
   title = "Título do documento"
   organization = "Organização responsável"
   url = "https://site-oficial.example/documento"
   kind = "official_documentation"
   topics = ["architecture", "design"]
   language = "en"
   license = "CC-BY-4.0"
   license_url = "https://creativecommons.org/licenses/by/4.0/"
   local_path = "data/raw/guia_de_arquitetura_aberta"
   include = ["*.pdf"]
   ingestion = "allowed_with_attribution"
   ```

4. Veja se o CLI encontra o arquivo e depois ingira apenas essa fonte:

   ```bash
   uv run anti-copilot-knowledge sources
   uv run anti-copilot-knowledge ingest --source guia_de_arquitetura_aberta
   ```

O `pypdf` extrai texto página por página; `page_number` fica nos metadados para podermos mostrar a citação. PDF digitalizado sem camada de texto precisa de OCR, que esta versão ainda não faz.

## 5. Como adicionar código de um repositório

Não coloque um diretório inteiro de dependências na base. Escolha um repositório público e relevante, confira a licença e registre a revisão exata para que a ingestão seja reproduzível.

1. Clone o repositório sob `data/raw/repositories/`. Essa pasta é ignorada pelo Git do Anti-Copilot:

   ```bash
   mkdir -p data/raw/repositories
   git clone --depth 1 https://github.com/ORGANIZACAO/REPOSITORIO.git \
     data/raw/repositories/repositorio_exemplo
   git -C data/raw/repositories/repositorio_exemplo rev-parse HEAD
   ```

2. Copie o hash exibido e registre o projeto. Use os padrões apenas para as linguagens que deseja estudar:

   ```toml
   [[sources]]
   id = "repositorio_exemplo"
   title = "Nome do projeto"
   organization = "Autor ou organização"
   url = "https://github.com/ORGANIZACAO/REPOSITORIO"
   kind = "open_source_repository"
   topics = ["architecture", "Python"]
   language = "en"
   license = "MIT"
   license_url = "https://github.com/ORGANIZACAO/REPOSITORIO/blob/HASH/LICENSE"
   revision = "HASH_DO_COMMIT"
   local_path = "data/raw/repositories/repositorio_exemplo"
   include = ["src/**/*.py", "src/**/*.java"]
   exclude = ["**/generated/**", "**/vendor/**"]
   ingestion = "allowed_with_attribution"
   ```

3. Inspecione o que será ingerido e execute só para esse ID:

   ```bash
   uv run anti-copilot-knowledge sources
   uv run anti-copilot-knowledge ingest --source repositorio_exemplo
   ```

O descobridor aceita `.py` e `.java` e ignora automaticamente `.git`, `node_modules`, ambientes virtuais, caches e diretórios de build. `include` deve ser restrito; adicione outros caminhos deliberadamente. Licença, autor, revisão e URL acompanham cada trecho recuperado.

## 6.1 Acervo Java e Python já preparado

O catálogo atual já aponta para **443 arquivos de código** (97 Python e 346 Java), além do documento de práticas do Google e de dois livros em PDF. Um `__init__.py` vazio é mantido no total de arquivos selecionados, mas naturalmente não gera trechos vetoriais. Os repositórios foram clonados com profundidade 1 para reduzir o download; o hash de cada revisão está em `data/catalog/sources.toml`.

| Fonte | Conteúdo escolhido | Licença declarada |
| --- | --- | --- |
| Requests | implementação Python da biblioteca HTTP | Apache-2.0 |
| Flask | implementação Python do framework | BSD-3-Clause |
| FastAPI | implementação Python do framework | MIT |
| Spring Petclinic | aplicação Java de exemplo da equipe Spring | Apache-2.0 |
| Java Design Patterns | exemplos de 24 padrões e conceitos relacionados | MIT |
| Guava | classes centrais e utilitários concorrentes do Google | Apache-2.0 |
| Think Java 2e | livro didático oficial em PDF | CC BY-NC-SA 4.0 |
| Think Python 2e | livro didático oficial em PDF | CC BY-NC 3.0 |

As contagens são dos arquivos que os padrões `include` selecionam, não de tudo que existe nos clones. Isso evita despejar no Chroma os testes e milhares de fontes que não foram escolhidas para o estudo. Os hashes de revisão registram exatamente o snapshot baixado nesta montagem; para atualizar uma fonte, baixe uma revisão nova, confira a licença e atualize o hash no catálogo.

Os PDFs estão em `data/raw/books/`, mas o `.gitignore` impede que livros sejam publicados acidentalmente no Git. As licenças dos dois livros permitem cópia e uso não comercial com atribuição; Think Java também exige compartilhar adaptações sob a mesma licença. Os livros comerciais Clean Code, GoF, Refactoring e Effective Java, além de Java Concurrency in Practice, ficam apenas como referências no catálogo. Não foram baixados nem indexados. A página pública do Cosmic Python informa CC BY-NC-ND; por isso também permanece como referência até uma avaliação específica dos termos para indexação.

## 7. Extração e chunking

- `.md`: primeiro divide por títulos Markdown; depois divide seções grandes em trechos menores, mantendo títulos nos metadados.
- `.txt`: divide recursivamente por parágrafos e linhas.
- `.pdf`: extrai cada página e mantém o número da página.
- `.py` e `.java`: usa `RecursiveCharacterTextSplitter.from_language`, configurado com separadores específicos da linguagem. Ele tenta manter blocos de código relacionados juntos; a divisão é estrutural por separadores, não um parser AST. Como enriquecimento separado, Python usa AST para registrar classes e funções de topo, e Java reconhece declarações de classe/interface/enum/record. Veja a [documentação oficial do splitter](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter).

Arquivos de texto sem conteúdo (por exemplo, alguns `__init__.py` que servem apenas como marcador de pacote) são ignorados; PDFs sem texto extraível continuam sendo erro e precisam de OCR.

O tamanho inicial é 900 caracteres e a sobreposição é 120. A sobreposição repete uma pequena borda entre trechos vizinhos para preservar continuidade. São valores iniciais que devem ser avaliados com consultas reais; não existe tamanho universalmente ideal. O E5 tem limite de contexto; chunks menores reduzem o risco de truncar o final do trecho.

IDs de chunk são hashes de fonte, caminho, página e posição. Ao reingerir uma fonte, o Chroma atualiza os chunks existentes e apaga os antigos que deixaram de existir. Isso torna a operação idempotente sem duplicar a mesma versão de um documento.

## 8. Embeddings e Chroma

`multilingual-e5-small` gera vetores de 384 dimensões e tem licença MIT ([cartão oficial do modelo](https://huggingface.co/intfloat/multilingual-e5-small)). O modelo é executado localmente pelo [FastEmbed](https://github.com/qdrant/fastembed) com ONNX Runtime; a primeira ingestão baixa seus pesos sem instalar PyTorch/CUDA. O código usa:

- `passage: ...` ao gerar vetores dos documentos;
- `query: ...` ao gerar o vetor da pergunta;
- normalização dos vetores e distância cosseno no Chroma.

Esses prefixos fazem parte do treinamento do E5; removê-los pode degradar recuperação. A coleção anota identificador e dimensão do modelo. Trocar o modelo exige registrar sua dimensão e integração no embedder, usar uma coleção nova e reindexar, pois vetores de espaços diferentes não devem ser misturados.

O Chroma recebe os vetores prontos (`embeddings=...`) junto dos textos (`documents=...`) e metadados (`metadatas=...`). Assim fica explícito no projeto onde embeddings são calculados e onde são persistidos. Consultas também passam `query_embeddings`; a função padrão automática do Chroma não é usada.

## 9. Comandos e aprendizagem

```bash
# Confere IDs, permissões declaradas e arquivos locais encontrados
uv run anti-copilot-knowledge sources

# Indexa todas as fontes explicitamente liberadas
uv run anti-copilot-knowledge ingest

# Indexa uma fonte específica
uv run anti-copilot-knowledge ingest --source google_engineering_practices

# Inspeciona os trechos mais próximos antes de envolver Gemini
uv run anti-copilot-knowledge search "Como equilibrar velocidade e qualidade numa revisão?"
```

Faça buscas manuais antes de avaliar a resposta do LLM. Se a fonte esperada não aparecer entre os primeiros resultados, o problema está na fonte, extração, chunking, modelo de embeddings ou consulta — não no prompt de geração.

## 9. Modelo generativo e privacidade

O modelo gerador é Gemini e recebe a pergunta mais os trechos recuperados. Embeddings são locais, mas o texto recuperado é enviado ao serviço Gemini para produzir a resposta. Se o serviço retornar indisponibilidade temporária HTTP 503, a interface mantém a busca local visível e permite tentar a mesma mensagem novamente. Use no acervo apenas material que você pode processar e enviar a esse provedor conforme as regras aplicáveis. A interface exibe título, arquivo, URL, página quando disponível e similaridade para facilitar a conferência.

## 10. Conversa design-first, SOS e aprovação

O formulário inicial e o chat são textuais, sem upload. Ao enviar o objetivo no formulário, o sistema faz primeiro uma busca vetorial local e mostra até cinco referências com trecho, origem e similaridade; isso não depende do Gemini. Depois, o chat usa a pergunta atual para buscar contexto novamente e só então solicita a resposta generativa. Uma checagem heurística recusa blocos que parecem código funcional para manter a conversa centrada em intenção e requisitos; como é uma heurística, ela pode ser ajustada em `app.py` se bloquear um texto legítimo.

`assistant.py` pede que o Gemini identifique o estado da conversa com um marcador interno (`INCOMPLETE`, `READY_FOR_CONFIRMATION` ou `RESCUE`). O marcador é removido antes da resposta aparecer na tela. A aplicação conta respostas incompletas consecutivas; quando a resposta atual completa a terceira falha, o modo SOS pode oferecer interfaces e esqueletos comentados, sem uma implementação funcional. Se a base não recuperar nenhum trecho, a aplicação informa isso e não trata a ausência de contexto como falha do aluno.

O status de prontidão só é aceito se a resposta contiver as cinco seções do blueprint e um bloco Mermaid. Isso é uma checagem estrutural simples, não uma prova de qualidade. A proposta pede confirmação explícita; só um `sim`, `confirmo`, `aprovo` ou equivalente exato libera o relatório.

O app desenha Mermaid em um componente isolado com modo `strict` e também mostra o bloco-fonte em `st.code`, cujo botão copia o texto. O componente carrega Mermaid pelo CDN, então o desenho precisa de conexão no navegador; o código continua visível se o desenho não carregar.

O relatório Markdown inclui objetivo, blueprint, diagramas e fontes recuperadas. A nota de maturidade é uma **nota de cobertura**: um ponto por seção obrigatória presente, até 5/5. Ela não mede automaticamente se as decisões são boas.

## 11. Próximas extensões

- OCR para PDFs digitalizados.
- Parser AST para associar funções/classes a imports e contexto de módulo com mais precisão.
- Avaliação com conjunto de perguntas e respostas esperadas, medindo recall@k antes de mexer no prompt.
- Reranker para reordenar os melhores candidatos sem substituir a busca vetorial.
- Sincronização e detecção de revisão de repositórios sem ingestão automática de dependências.
