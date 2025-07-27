import html
import streamlit as st
import requests
import os

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8002")

st.set_page_config(page_title="RAG App Interface", layout="wide")
st.title("📚 RAG FastAPI Interface")

# --- Sidebar Actions ---
st.sidebar.header("🔧 Admin Panel")

# Upload Section
st.sidebar.subheader("📤 Upload Documents")
with st.sidebar.form("upload_form"):
    uploaded_files = st.file_uploader("Choose documents", accept_multiple_files=True, type=["pdf", "txt", "docx"])
    submit_upload = st.form_submit_button("Upload")
    if submit_upload and uploaded_files:
        files = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
        with st.spinner("Uploading and processing..."):
            res = requests.post(f"{API_BASE}/ingest", files=files)
            st.sidebar.success("✅ Upload initiated!")
            st.sidebar.json(res.json())

# Inspect Section
st.sidebar.subheader("🔍 Inspect Weaviate Structure")
if st.sidebar.button("View Structure"):
    with st.spinner("Fetching structure..."):
        res = requests.get(f"{API_BASE}/inspect")
        if res.ok:
            structure = res.json()
            st.sidebar.success("✅ Structure retrieved")
            st.sidebar.json(structure)
        else:
            st.sidebar.error("❌ Failed to retrieve structure")

# Clear Index Section
st.sidebar.subheader("🧹 Clear Weaviate Index")
clear_index = st.sidebar.text_input("Enter index name (leave blank for ALL):")
if st.sidebar.button("Clear Index"):
    with st.spinner("Clearing index..."):
        res = requests.delete(f"{API_BASE}/clear", json={"index_name": clear_index or None})
        if res.status_code in [200, 207]:
            st.sidebar.success("✅ Clear operation completed")
            st.sidebar.json(res.json())
        else:
            st.sidebar.error("❌ Failed to clear index")
            st.sidebar.json(res.json())

# --- Main Area: Query Section ---
st.subheader("💬 Ask a Question")
query_text = st.text_input("Enter your question:", "")
if st.button("Submit Query") and query_text:
    with st.spinner("Processing query..."):
        res = requests.post(f"{API_BASE}/query", json={"query": query_text})
        if res.ok:
            output = res.json()
            st.success("✅ Answer retrieved:")
            st.markdown(f"**Answer:** {output['answer']}")
            st.markdown(f"**Metadata used:** {output['metadata_used']}")

            sources = output.get("sources", [])
            if isinstance(sources, str):
                sources = [sources]

            if sources:
                st.markdown("**Sources:**")
                source_items = ""

                for src in sources:
                    safe_src = html.escape(str(src)).replace("\n", "<br>")
                    source_items += f"<div style='margin-bottom:10px;'>{safe_src}</div>"

                st.markdown(
                    f"""
                    <div style="
                        background-color: #f6f8fa;
                        padding: 12px;
                        border-radius: 6px;
                        max-height: 250px;
                        overflow-y: auto;
                        border: 1px solid #ccc;
                    ">
                        {source_items}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:
            st.error("❌ Query failed")
