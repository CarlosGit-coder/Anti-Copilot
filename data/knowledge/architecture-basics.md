# Fundamentos de arquitetura de software

## Requisitos e limites
Antes de escolher tecnologias, esclareça quem usa o sistema, quais tarefas precisa realizar, quais dados entram e saem e quais restrições existem. Separe requisitos funcionais de qualidades esperadas, como segurança, disponibilidade, desempenho e facilidade de manutenção. Registre também o que está fora do escopo.

## Entidades e responsabilidades
Modele primeiro os conceitos centrais do domínio e as regras que protegem seus dados. Cada módulo deve ter uma responsabilidade coesa e depender de contratos claros. Evite criar abstrações ou padrões sem uma necessidade concreta que eles resolvam.

## SOLID em termos práticos
Responsabilidade única significa que um módulo deve ter um motivo principal para mudar. Inversão de dependência recomenda que regras de alto nível dependam de interfaces estáveis, e não de detalhes como banco ou provedor externo. Esses princípios ajudam a trocar infraestrutura e tornam os limites do sistema mais compreensíveis.

## Decisões e falhas
Para cada integração externa, defina o que acontece quando ela falha, expira ou retorna dados inválidos. Considere validação na entrada, mensagens de erro úteis, registros sem segredos e limites de repetição. Documente decisões relevantes com contexto, alternativas consideradas e consequências.

## Diagramas
Use diagrama de componentes para mostrar módulos e dependências; use diagrama de sequência para explicar a ordem das chamadas em um cenário importante. Um diagrama deve representar uma decisão ou fluxo que o time precisa discutir, sem tentar desenhar todos os detalhes da implementação.
