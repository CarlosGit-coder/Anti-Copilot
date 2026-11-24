"""Interface de chat Streamlit do Anti-Copilot."""

from __future__ import annotations

from typing import Any

import streamlit as st

from anti_copilot.application.mentor import MentorUnavailable, ProjectMentor
from anti_copilot.infrastructure.chroma_fastembed import ChromaFastEmbedKnowledge
from anti_copilot.infrastructure.n8n_client import N8nResponseGenerator


@st.cache_resource
def get_mentor() -> ProjectMentor:
    return ProjectMentor(ChromaFastEmbedKnowledge(), N8nResponseGenerator())


def render_sources(sources: list[dict[str, Any]]) -> None:
    with st.expander("Fontes recuperadas do ChromaDB", expanded=False):
        for item in sources:
            metadata = item["metadata"]
            label = metadata.get("section", "Trecho")
            source_title = metadata.get("source_title", "Documento local")
            file_path = metadata.get("file_path", "")
            distance = item["distance"]
            st.markdown(f"**{label}** · {source_title} · `{file_path}` · distância {distance:.3f}")
            source_url = metadata.get("source_url", "")
            if source_url:
                st.markdown(f"[Abrir fonte oficial]({source_url})")
            st.caption(item["text"])


def main() -> None:
    st.set_page_config(page_title="Anti-Copilot", page_icon="🧠", layout="centered")
    st.title("🧠 Anti-Copilot")
    st.caption("A memória do projeto que ajuda a recuperar decisões, orientações e contexto.")
    st.markdown(
        "Este MVP usa notas da documentação oficial do **FastAPI** como acervo de demonstração. "
        "Pergunte sobre a documentação; as fontes recuperadas aparecem abaixo da resposta."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                render_sources(message["sources"])

    prompt = st.chat_input("Pergunte algo sobre o contexto documentado do projeto...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Buscando trechos no acervo e consultando o mentor local..."):
                answer, evidence = get_mentor().ask(prompt)
            st.markdown(answer)
            render_sources(evidence)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "sources": evidence}
            )
        except MentorUnavailable as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Não foi possível concluir a consulta: {error}")

