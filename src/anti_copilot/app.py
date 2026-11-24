"""Interface Streamlit para conversa, diagramas e aprovação do blueprint."""

from datetime import datetime
import json
import re
import unicodedata

import streamlit as st
import streamlit.components.v1 as components

from anti_copilot.assistant import ArchitectureAssistant
from anti_copilot.config import settings
from anti_copilot.rag import KnowledgeBase


CODE_LINE_PATTERN = re.compile(
    r"^\s*(?:def\s+\w+\s*\(|class\s+\w+\s*[:({]|"
    r"(?:from\s+\w[\w.]*\s+import|import\s+\w[\w.]*)|"
    r"public\s+(?:static\s+)?(?:class|interface|void|[A-Z]\w*\s+\w+\s*\()|"
    r"(?:const|let|function)\s+\w+|@\w+)"
)


@st.cache_resource
def get_assistant() -> ArchitectureAssistant:
    return ArchitectureAssistant(KnowledgeBase(settings), settings)


def _normalize_confirmation(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9 ]", " ", without_accents).strip()


def _is_explicit_confirmation(text: str) -> bool:
    confirmation = _normalize_confirmation(text)
    return confirmation in {
        "sim",
        "sim pode gerar",
        "sim pode gerar o relatorio",
        "sim esta aprovado",
        "confirmo",
        "sim confirmo",
        "confirmo o blueprint",
        "confirmo este blueprint",
        "aprovo",
        "aprovado",
        "pode gerar o relatorio",
        "gerar relatorio",
    }


def _looks_like_raw_code(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    code_lines = sum(bool(CODE_LINE_PATTERN.match(line)) for line in lines)
    if len(lines) >= 3 and code_lines >= 2 and code_lines / len(lines) >= 0.25:
        return True
    return bool(lines and CODE_LINE_PATTERN.match(lines[0]))


def _render_mermaid(diagram: str) -> None:
    # Mermaid roda em iframe isolado e em modo strict; st.code oferece cópia do texto.
    diagram_literal = json.dumps(diagram)
    markup = f"""<!doctype html>
<html><head><style>
body {{ margin: 0; font-family: sans-serif; }}
#diagram {{ overflow: auto; text-align: center; }}
#error {{ color: #a33; white-space: pre-wrap; }}
</style></head><body>
<div id="diagram"></div><div id="error"></div>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: false, securityLevel: "strict", theme: "neutral" }});
  try {{
    const {{ svg }} = await mermaid.render("anti-copilot-blueprint", {diagram_literal});
    document.getElementById("diagram").innerHTML = svg;
  }} catch (error) {{
    document.getElementById("error").textContent = "Não foi possível desenhar o diagrama. O código Mermaid está abaixo.";
  }}
</script></body></html>"""
    components.html(markup, height=420, scrolling=True)
    st.code(diagram, language="mermaid")


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for diagram in message.get("diagrams", []):
            _render_mermaid(diagram)


def _maturity_score(blueprint: str) -> int:
    """Nota de cobertura: um ponto por dimensão documentada no blueprint aprovado."""
    required = (
        "### 1. Objetivo e requisitos",
        "### 2. Entidades e regras de domínio",
        "### 3. Módulos e responsabilidades",
        "### 4. Dependências e tratamento de falhas",
        "### 5. Padrões e diagrama",
    )
    return sum(heading in blueprint for heading in required)


def _build_report(objective: str, blueprint: str, diagrams: list[str], sources: list[dict]) -> str:
    score = _maturity_score(blueprint)
    lines = [
        "# Relatório de Aprovação Arquitetural",
        "",
        f"**Projeto:** {objective}",
        f"**Gerado em:** {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "**Estado:** confirmado explicitamente pelo usuário",
        "",
        "## Nota de maturidade de design",
        f"**{score}/5 dimensões documentadas.** Um ponto é atribuído para cada seção obrigatória presente no blueprint; a nota mede cobertura do relatório, não qualidade automática da arquitetura.",
        "",
        "## Blueprint aprovado",
        "",
        blueprint,
        "",
        "## Diagramas Mermaid",
        "",
    ]
    if diagrams:
        for index, diagram in enumerate(diagrams, start=1):
            lines.extend([f"### Diagrama {index}", "", "```mermaid", diagram, "```", ""])
    else:
        lines.extend(["Nenhum diagrama foi registrado.", ""])

    lines.extend(["## Fontes recuperadas durante a validação", ""])
    unique_sources: dict[tuple[str, str], dict] = {}
    for result in sources:
        metadata = result["metadata"]
        unique_sources[(metadata["source_id"], metadata["file_path"])] = metadata
    for metadata in unique_sources.values():
        location = metadata["file_path"]
        if "page_number" in metadata:
            location += f", página {metadata['page_number']}"
        if "section" in metadata:
            location += f", seção {metadata['section']}"
        lines.append(
            f"- [{metadata['source_title']}]({metadata['source_url']}) — {location}; "
            f"{metadata['organization']}; licença {metadata['license']}."
        )
    return "\n".join(lines).rstrip() + "\n"


def _reset_conversation(objective: str) -> None:
    st.session_state.messages = []
    st.session_state.incomplete_streak = 0
    st.session_state.active_objective = objective
    st.session_state.awaiting_confirmation = False
    st.session_state.approved_blueprint = None
    st.session_state.approved_diagrams = []
    st.session_state.approved_sources = []
    st.session_state.last_sources = []
    st.session_state.objective_retrieved_for = None
    st.session_state.objective_sources = []
    st.session_state.objective_search_error = None
    st.session_state.retry_message = None


def main() -> None:
    st.set_page_config(page_title="Anti-Copilot", page_icon="🧭", layout="centered")
    st.title("🧭 Anti-Copilot")
    st.caption("Planeje e valide a arquitetura antes de começar a programar.")

    with st.form("objective_form"):
        objective_draft = st.text_input(
            "O que você quer construir?",
            placeholder="Ex.: sistema de agendamento de consultas para uma clínica",
            key="objective",
        )
        start_objective = st.form_submit_button("Buscar na base e iniciar planejamento")

    if start_objective:
        if not objective_draft.strip():
            st.warning("Descreva o que quer construir antes de iniciar.")
            return
        if _looks_like_raw_code(objective_draft):
            st.warning("Descreva sua intenção em linguagem natural. Não cole código funcional.")
            return
        _reset_conversation(objective_draft.strip())
        st.session_state.objective_started = True

    if not st.session_state.get("objective_started"):
        st.info("Descreva seu objetivo e clique em “Buscar na base e iniciar planejamento”.")
        return

    objective = st.session_state.active_objective
    st.session_state.setdefault("incomplete_streak", 0)
    st.session_state.setdefault("awaiting_confirmation", False)
    st.session_state.setdefault("approved_blueprint", None)
    st.session_state.setdefault("approved_diagrams", [])
    st.session_state.setdefault("approved_sources", [])
    st.session_state.setdefault("last_sources", [])
    st.session_state.setdefault("objective_retrieved_for", None)
    st.session_state.setdefault("objective_sources", [])
    st.session_state.setdefault("objective_search_error", None)
    st.session_state.setdefault("retry_message", None)

    # O objetivo faz uma busca local imediatamente, antes de qualquer chamada ao Gemini.
    if st.session_state.objective_retrieved_for != objective:
        try:
            with st.spinner("Buscando referências para o objetivo na base vetorial…"):
                st.session_state.objective_sources = get_assistant().knowledge.search(
                    objective, limit=5
                )
            st.session_state.objective_search_error = None
        except Exception as error:
            st.session_state.objective_sources = []
            st.session_state.objective_search_error = str(error)
        st.session_state.objective_retrieved_for = objective

    if st.session_state.objective_search_error:
        st.warning(
            "Não consegui consultar o banco vetorial agora. "
            f"Detalhe: {st.session_state.objective_search_error}"
        )
    elif st.session_state.objective_sources:
        with st.expander("Referências encontradas para este objetivo", expanded=True):
            st.caption("Busca vetorial feita antes da conversa com a IA. Similaridade não é uma nota de qualidade.")
            for result in st.session_state.objective_sources:
                metadata = result["metadata"]
                location = metadata["file_path"]
                if "page_number" in metadata:
                    location += f" · pág. {metadata['page_number']}"
                st.markdown(
                    f"**{metadata['source_title']}** · `{location}` · "
                    f"[origem]({metadata['source_url']}) · "
                    f"similaridade {result['similarity']:.2f}"
                )
                st.write(result["text"][:700])
    else:
        st.info(
            "A busca do objetivo não encontrou trechos. Confira se a base foi indexada "
            "ou tente reformular a descrição."
        )

    if st.session_state.incomplete_streak >= 3:
        st.info("Modo SOS ativo: o assistente pode mostrar interfaces e esqueletos comentados para destravar o planejamento.")

    for message in st.session_state.messages:
        _render_message(message)

    retry_prompt = st.session_state.get("retry_message")
    retry_clicked = False
    if retry_prompt:
        retry_clicked = st.button("Tentar novamente a última mensagem", key="retry_gemini")
    typed_text = st.chat_input("Responda à pergunta de arquitetura…")
    user_text = retry_prompt if retry_clicked else typed_text
    if retry_clicked or typed_text:
        st.session_state.retry_message = None

    if user_text:
        if _looks_like_raw_code(user_text):
            st.warning("Envie a intenção ou os requisitos em texto; a entrada de código funcional é bloqueada.")
            return
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        if st.session_state.awaiting_confirmation and _is_explicit_confirmation(user_text):
            st.session_state.approved_blueprint = st.session_state.pending_blueprint
            st.session_state.approved_diagrams = st.session_state.pending_diagrams
            st.session_state.approved_sources = st.session_state.pending_sources
            st.session_state.awaiting_confirmation = False
            confirmation_message = {
                "role": "assistant",
                "content": "Blueprint confirmado. O relatório de aprovação está pronto para download abaixo.",
                "diagrams": [],
            }
            st.session_state.messages.append(confirmation_message)
            _render_message(confirmation_message)
        else:
            st.session_state.approved_blueprint = None
            st.session_state.approved_diagrams = []
            st.session_state.approved_sources = []
            if st.session_state.awaiting_confirmation:
                st.session_state.awaiting_confirmation = False
                st.session_state.incomplete_streak = 0
            history = []
            for message in st.session_state.messages:
                prior_content = message["content"]
                for diagram in message.get("diagrams", []):
                    prior_content += f"\n```mermaid\n{diagram}\n```"
                history.append({"role": message["role"], "content": prior_content})
            try:
                with st.spinner("Consultando a base vetorial e avaliando o planejamento…"):
                    answer, sources, status, diagrams = get_assistant().respond(
                        objective,
                        user_text,
                        history,
                        st.session_state.incomplete_streak,
                    )
                if status == "INCOMPLETE":
                    st.session_state.incomplete_streak += 1
                elif status == "RESCUE":
                    st.session_state.incomplete_streak = max(3, st.session_state.incomplete_streak)
                elif status == "READY_FOR_CONFIRMATION":
                    st.session_state.incomplete_streak = 0
                    st.session_state.awaiting_confirmation = True
                    st.session_state.pending_blueprint = answer
                    st.session_state.pending_diagrams = diagrams
                    st.session_state.pending_sources = sources

                assistant_message = {"role": "assistant", "content": answer, "diagrams": diagrams}
                st.session_state.messages.append(assistant_message)
                st.session_state.last_sources = sources
                _render_message(assistant_message)
            except Exception as error:
                st.session_state.messages.pop()
                error_text = str(error)
                normalized_error = error_text.casefold()
                if "503" in normalized_error or "service_unavailable" in normalized_error:
                    st.session_state.retry_message = user_text
                    st.warning(
                        "A busca na base local foi feita, mas o Gemini está temporariamente "
                        "indisponível (HTTP 503). Suas fontes continuam visíveis acima. "
                        "Aguarde um pouco e use o botão para tentar novamente."
                    )
                else:
                    st.error(f"Não foi possível gerar uma resposta: {error_text}")

    if st.session_state.get("last_sources"):
        with st.expander("Fontes recuperadas pelo RAG"):
            for source in st.session_state.last_sources:
                metadata = source["metadata"]
                location = metadata["file_path"]
                if "page_number" in metadata:
                    location += f" · pág. {metadata['page_number']}"
                if "section" in metadata:
                    location += f" · {metadata['section']}"
                st.markdown(
                    f"**{metadata['source_title']}** · `{location}` · "
                    f"[abrir fonte]({metadata['source_url']}) · "
                    f"licença `{metadata['license']}` · "
                    f"similaridade {source['similarity']:.2f}"
                )

    if st.session_state.get("approved_blueprint"):
        report = _build_report(
            objective,
            st.session_state.approved_blueprint,
            st.session_state.approved_diagrams,
            st.session_state.approved_sources,
        )
        st.download_button(
            "Baixar relatório arquitetural (.md)",
            data=report,
            file_name="anti-copilot-blueprint.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
