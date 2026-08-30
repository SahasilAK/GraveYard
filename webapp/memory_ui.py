import streamlit as st
from scrum_team.memory_store import search_memory, delete_memory, create_store

def render_memory_manager():
    st.header("Memory Manager")
    st.caption("Manage persistent cross-project knowledge.")

    store = create_store()
    
    # List namespaces
    namespaces = store.list_namespaces()
    tabs = st.tabs([str(ns) for ns in namespaces] if namespaces else ["No memories"])

    for ns, tab in zip(namespaces, tabs):
        with tab:
            items = store.search(ns)
            for item in items:
                with st.expander(f"Key: {item.key}"):
                    st.json(item.value)
                    col1, col2 = st.columns([1, 4])
                    if col1.button("Delete", key=f"del_{ns}_{item.key}"):
                        delete_memory(ns, item.key)
                        st.rerun()
            
            st.divider()
            if st.button(f"Clear namespace {ns}", type="primary", key=f"clear_{ns}"):
                for item in items:
                    delete_memory(ns, item.key)
                st.rerun()
