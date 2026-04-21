"""
Frontend built on Streamlit.
"""
import streamlit as st
import time
from streamlit_option_menu import option_menu
from api_client import login_user_api, get_chat_response_api, get_all_users_api, get_all_roles_api, \
add_new_role_api, delete_role_api, get_unique_roles_api, get_unique_categories_api, \
get_categories_for_role_api, add_user_api, delete_user_api

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("app/style.css")

if not st.session_state.get("authenticated"):
    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 2])
        with sub_col2:
            st.image("app/images/ucu_logo.png", use_container_width=True)
        
        st.markdown("<h1 class='centered-title'>Вхід до системи</h1>", unsafe_allow_html=True)
       
        with st.container(border=True):
            username_input = st.text_input("Логін", placeholder="Введіть ваш логін")
            password_input = st.text_input("Пароль", type="password", placeholder="Введіть ваш пароль")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            login_button = st.button("Увійти", use_container_width=True)
            
            if login_button:
                role = login_user_api(username_input, password_input)
                if role:
                    st.session_state.authenticated = True
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Неправильний логін або пароль")
    st.stop()
else:
    with st.sidebar:
        col_side1, col_side2, col_side3 = st.columns([1, 3, 1])
        
        with col_side2:
            st.image("app/images/ucu_logo.png", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        menu = option_menu(
            menu_title="Навігація", 
            menu_icon="none",
            options=["Чат підтримки", "Адмін-панель"] if st.session_state.get("role") == "Адмін" else ["Чат підтримки"],
            icons=["chat-dots", "gear"],  
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": "#fafafa", "border-radius": "10px"},
                "menu-title": {"font-size": "16px", "text-transform": "uppercase", "font-weight": "bold", "color": "#888"},
                "menu-icon": {"display": "none"},
                "icon": {"color": "#444", "font-size": "16px"}, 
                "nav-link": {
                    "font-size": "16px", 
                    "text-align": "left", 
                    "margin": "5px", 
                    "--hover-color": "#eee",
                    "border-radius": "8px",
                    "display": "flex",
                    "align-items": "center"
                },
                "nav-link-selected": {
                    "background-color": "#f0dddd",
                    "color": "black !important",
                    "font-weight": "normal",
                }
            }
        )
        st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("Вийти", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    if menu == "Чат підтримки":
        st.title("Чат підтримки працівників УКУ")
        st.markdown("---")
        if "messages" not in st.session_state:
            st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("Яке у вас питання?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Шукаю інформацію..."):
                    try:
                        answer = get_chat_response_api(prompt, st.session_state.role)
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Помилка: {e}")
    elif menu == "Адмін-панель":
        st.title("Панель адміністратора 🛠️")
        tab1, tab2, tab3 = st.tabs(["Користувачі", "Ролі та Права", "Додати/Видалити"])
        with tab1:
            st.subheader("Список користувачів")
            current_role = st.session_state.get("role")
            users = get_all_users_api(current_role)
            if users:
                st.table(users)
            else:
                st.warning("Не вдалося завантажити список користувачів або доступ заборонено.")
        with tab2:
            st.subheader("Керування ролями")
            st.write("**Список ролей і їх прав**")
            roles = get_all_roles_api(current_role)
            if roles:
                st.table(roles)
            else:
                st.warning("Не вдалося завантажити список ролей або доступ заборонено.")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**Додати права для ролі**")
                unique_roles = get_unique_roles_api(current_role)
                role_options = ["+ Створити нову роль..."] + unique_roles
                role_select = st.selectbox("Оберіть роль", role_options)
                if role_select == "+ Створити нову роль...":
                    new_role_name = st.text_input("Введіть назву нової ролі")
                else:
                    new_role_name = role_select
                unique_categories = get_unique_categories_api(current_role)
                category_name = st.selectbox("Категорія файлу, до якого ви хочете дати доступ", unique_categories) 
                if st.button("Зберегти нову роль"):
                    if new_role_name and category_name:
                        success, message = add_new_role_api(new_role_name, category_name, st.session_state.get("role"))
                        if success:
                            st.success(message)
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error(f"Не вдалося додати: {message}")
                            time.sleep(3)
                            st.rerun()
                    else:
                        st.warning("Будь ласка, заповніть обидва поля.")
            with col2:
                st.write("**Видалити права**")
                role_name = st.selectbox("Оберіть роль для видалення", unique_roles)
                categories_for_role = get_categories_for_role_api(role_name, current_role)
                category_name = st.selectbox("Категорія файлу, до якого ви хочете видалити доступ", categories_for_role)
                if st.button("Видалити"):
                    if role_name and category_name:
                        success, message = delete_role_api(role_name, category_name, st.session_state.get("role"))
                        if success:
                            st.success(message)
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error(f"Не вдалося видалити: {message}")
                    else:
                        st.warning("Будь ласка, заповніть обидва поля.")
        with tab3:
            st.subheader("Керування акаунтами")
            with st.form("add_user_form", clear_on_submit=True):
                new_user = st.text_input("Логін")
                new_password = st.text_input("Пароль", type="password")
                new_role = st.selectbox("Оберіть роль для нового користувача", unique_roles)
                submit_button = st.form_submit_button("Створити користувача")
                msg_placeholder = st.empty()
                if submit_button:
                    if new_user and new_password and new_role:
                        success, message = add_user_api(new_user, new_password, new_role, current_role)
                        if success:
                            msg_placeholder.success(f"{message}")
                            time.sleep(3)
                            msg_placeholder.empty()
                            st.rerun()
                        else:
                            st.error(f"Помилка: {message}")
                            time.sleep(3)
                            st.rerun()
                    else:
                        st.warning("Заповніть усі поля.")
            st.divider()
            with st.form("delete_user_form", clear_on_submit=True):
                delete_user = st.text_input("Логін для видалення")
                delete_button = st.form_submit_button("Видалити користувача")
                msg_placeholder = st.empty()
                if delete_button:
                    if delete_user:
                        success, message = delete_user_api(delete_user, current_role)
                        if success:
                            msg_placeholder.success(f"{message}")
                            time.sleep(3)
                            msg_placeholder.empty()
                            st.rerun()
                        else:
                            st.error(f"Помилка: {message}")
                            time.sleep(3)
                            st.rerun()
                    else:
                        st.warning("Будь ласка, введіть логін для видалення.")
