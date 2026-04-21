"""
This module is used to send requests from frontend to backend.
"""

import requests

BACKEND_URL = "http://fastapi_backend:8000"

def get_all_users_api(role):
    try:
        response = requests.get(f"{BACKEND_URL}/admin/users", params={"current_user_role": role})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"Connection error (users): {e}")
        return []

def get_all_roles_api(role):
    try:
        response = requests.get(f"{BACKEND_URL}/admin/roles", params={"current_user_role": role})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"Connection error (roles): {e}")
        return []

def get_unique_roles_api(admin_role):
    try:
        response = requests.get(f"{BACKEND_URL}/admin/unique-roles", params={"current_user_role": admin_role})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        return []

def get_unique_categories_api(admin_role):
    try:
        response = requests.get(f"{BACKEND_URL}/admin/unique-categories", params={"current_user_role": admin_role})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        return []

def get_categories_for_role_api(role_name, admin_role):
    try:
        response = requests.get(f"{BACKEND_URL}/admin/categories/{role_name}", params={"current_user_role": admin_role})
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        return []

def login_user_api(username, password):
    try:
        response = requests.post(f"{BACKEND_URL}/login", json={"username": username, "password": password})
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def get_chat_response_api(query, role):
    try:
        response = requests.post(f"{BACKEND_URL}/chat", json={"query": query, "role": role})
        if response.status_code == 200:
            return response.json().get("answer")
        return "Помилка зв'язку з бекендом."
    except Exception as e:
        return f"Помилка з'єднання: {str(e)}"

def add_new_role_api(new_role, category, admin_role):
    try:
        params = {"role": new_role, "category": category, "current_user_role": admin_role}
        response = requests.post(f"{BACKEND_URL}/admin/add-role", params=params) 
        if response.status_code == 200:
            return True, response.json().get("message", "Роль додана")
        error_detail = response.json().get("detail", "Помилка сервера")
        return False, error_detail
    except Exception as e:
        return False, f"Помилка мережі: {str(e)}"

def delete_role_api(role, category, admin_role):
    try:
        params = {"role": role, "category": category, "current_user_role": admin_role}
        response = requests.post(f"{BACKEND_URL}/admin/delete-role", params=params) 
        if response.status_code == 200:
            return True, response.json().get("message", "Роль видалена")
        return False, response.json().get("detail", "Помилка сервера")
    except Exception as e:
        return False, f"Помилка мережі: {str(e)}"

def add_user_api(username, password, role, admin_role):
    try:
        payload = {"username": username, "password": password, "role": role}
        params = {"current_user_role": admin_role}
        response = requests.post(f"{BACKEND_URL}/admin/add-user", json=payload, params=params)
        if response.status_code == 200:
            return True, response.json().get("message", "Юзера додано")
        error_detail = response.json().get("detail", "Помилка сервера")
        return False, error_detail
    except Exception as e:
        return False, f"Помилка мережі: {str(e)}"

def delete_user_api(username, admin_role):
    try:
        response = requests.delete(f"{BACKEND_URL}/admin/delete-user/{username}", params={"current_user_role": admin_role})
        if response.status_code == 200:
            return True, response.json().get("message", "Юзера видалено")
        error_detail = response.json().get("detail", "Помилка сервера")
        return False, error_detail
    except Exception as e:
        return False, f"Помилка мережі: {str(e)}"
