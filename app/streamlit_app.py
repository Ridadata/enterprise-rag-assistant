import httpx
import streamlit as st


API_URL = "http://localhost:8000/ask"

st.set_page_config(page_title="Enterprise RAG Assistant", page_icon=":material/search:", layout="wide")

st.title("Enterprise Data & IT Knowledge Assistant")

question = st.chat_input("Ask about IT, data engineering, incidents, policies, or runbooks")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            response = httpx.post(API_URL, json={"question": question}, timeout=30)
            response.raise_for_status()
            payload = response.json()
            answer = payload["answer"]
            st.markdown(answer)
            st.caption(f"Confidence: {payload['confidence']}")
            if payload["sources"]:
                st.subheader("Sources")
                for source in payload["sources"]:
                    st.markdown(
                        f"- **{source['title']}** (`{source['chunk_id']}`): "
                        f"{source['excerpt']}"
                    )
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as exc:
            error = f"API request failed: {exc}"
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})
