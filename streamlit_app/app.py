import streamlit as st
import os
import sys
from database import verify_user, get_allowed_categories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from final_project import retrieve_and_generate

st.set_page_config(page_title="UCU Employee Support", page_icon="🎓")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_form():
    st.title("Вхід у систему")
    with st.form("login"):
        username = st.text_input("Логін")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Увійти")
        
        if submit:
            role = verify_user(username, password)
            if role:
                st.session_state["authenticated"] = True
                st.session_state["role"] = role
                st.success("Успішний вхід!")
                st.rerun()
            else:
                st.error("Неправильний логін або пароль")

if not st.session_state["authenticated"]:
    login_form()
else:
    st.sidebar.write(f"Ви увійшли як: **{st.session_state['role']}**")
    if st.sidebar.button("Вийти"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.title("UCU Employee Support System 🎓")
    st.markdown("Поставте запитання про внутрішні процедури чи документи УКУ.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Яке у вас запитання?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Шукаю інформацію в документах УКУ..."):
                try:
                    allowed = get_allowed_categories(st.session_state["role"])
                    response = retrieve_and_generate.run_rag_pipeline(prompt, allowed_categories=allowed)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Виникла помилка: {e}")
