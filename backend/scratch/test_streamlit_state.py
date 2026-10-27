import streamlit as st

st.text_input("Test", key="my_widget")

if st.button("Clear"):
    del st.session_state["my_widget"]
    st.rerun()
