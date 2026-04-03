import streamlit as st
from streamlit_option_menu import option_menu
import os
import sys
import time
from services.iam_service import (
    verify_user, 
    get_allowed_categories, 
    get_all_users, 
    add_new_user, 
    delete_user, 
    add_new_role, 
    delete_role,
    get_unique_roles,
    get_categories_for_role,
    get_all_roles_with_permissions
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services import rag_service
from services.qdrant_service import get_unique_categories_from_qdrant

def reset_fields(keys_with_defaults: dict):
    for key, default_value in keys_with_defaults.items():
        st.session_state[key] = default_value

st.set_page_config(page_title="UCU Employee Support", page_icon="🎓", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# --- ЛОГІКА ВХОДУ ---
if not st.session_state["authenticated"]:
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
                st.rerun()
            else:
                st.error("Неправильний логін або пароль")

# --- ОСНОВНИЙ ІНТЕРФЕЙС ---
else:
    if st.session_state["role"] == "Адмін":
        with st.sidebar:
            menu = option_menu(
                menu_title="Навігація", 
                options=["Чат підтримки", "Адмін-панель"],
                icons=["chat-dots", "gear"], 
                default_index=0,
            )
    else:
        with st.sidebar:
            menu = option_menu(
                menu_title="Навігація", 
                options=["Чат підтримки"],
                icons=["chat-dots", "gear"],
                menu_icon="cast", 
                default_index=0,
            )

    if st.sidebar.button("Вийти"):
        st.session_state.clear()
        st.rerun()

    # --- СТОРІНКА ЧАТУ ---
    if menu == "Чат підтримки":
        st.title("UCU Employee Support System 🎓")
        
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
                with st.spinner("Шукаю інформацію..."):
                    try:
                        allowed = get_allowed_categories(st.session_state["role"])
                        response = rag_service.run_rag_pipeline(prompt, allowed_categories=allowed)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Помилка: {e}")

    # --- СТОРІНКА АДМІНА ---
    elif menu == "Адмін-панель":
        st.title("Панель адміністратора 🛠️")

        available_roles = get_unique_roles()
        
        tab1, tab2, tab3 = st.tabs(["Користувачі", "Ролі та Права", "Додати/Видалити"])

        with tab1:
            st.subheader("Список користувачів")
            users = get_all_users()
            if users:
                st.table(users)
            else:
                st.info("Користувачів не знайдено.")

        with tab2:
            st.subheader("Керування ролями")
            st.write("Список ролей і їх прав")
            roles = get_all_roles_with_permissions()
            if roles:
                st.table(roles)
            else:
                st.info("У базі поки немає жодної ролі.")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.write("**Додати права до ролі**")
                role_options = available_roles + ["➕ Створити нову роль..."]
                
                selected_role_opt = st.selectbox("Оберіть роль", role_options, key="select_role")
                
                if selected_role_opt == "➕ Створити нову роль...":
                    r_name = st.text_input("Введіть назву нової ролі", key="name_role")
                else:
                    r_name = selected_role_opt
                available_categories = get_unique_categories_from_qdrant()
                r_cat = st.selectbox(
                    "Категорія файлу, до якого ви хочете дати доступ", 
                    available_categories,
                    key="choose_category"
                )
                if st.button("Зберегти роль"):
                    add_new_role(r_name, r_cat)
                    st.success(f"Ролі {r_name} додано доступ до {r_cat}")
                    time.sleep(5)
                    st.rerun()
            
            with col2:
                st.write("**Видалити права**")
                dr_name = st.selectbox("Роль для видалення", available_roles, key="delete_role")
                role_categories = get_categories_for_role(dr_name)
                if role_categories:
                    dr_cat = st.selectbox("Оберіть категорію для видалення", role_categories, key="choose_category_delete")
                    if st.button("Видалити доступ", type="secondary"):
                        delete_role(dr_name, dr_cat)
                        st.warning(f"Доступ до категорії '{dr_cat}' для ролі '{dr_name}' видалено.")
                        time.sleep(5)
                        st.rerun()

        with tab3:
            st.subheader("Керування акаунтами")
            new_u = st.text_input("Логін", key="login")
            new_p = st.text_input("Пароль", type="password", key="password")
            new_r = st.selectbox("Оберіть роль для нового користувача", available_roles, key="available_roles")
            if st.button("Створити користувача"):
                add_new_user(new_u, new_p, new_r)
                st.success(f"Користувача {new_u} створено!")
                time.sleep(5)
                st.rerun()
            
            st.divider()
            del_u = st.text_input("Логін для видалення", key="login_delete")
            if st.button("Видалити користувача", type="primary"):
                delete_user(del_u)
                st.error(f"Користувача {del_u} видалено")
                time.sleep(5)
                st.rerun()
