"""
Backend fucntions built on FastAPI. All these functions are used to communicate with 
PostreSQL for authorization and RAG pipeline for answering user queries.
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from app.services import iam_service
from app.services import rag_service
from app.services import qdrant_service

app = FastAPI(title="UCU Support RAG API")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    query: str
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@app.post("/login")
async def login(req: LoginRequest):
    user = iam_service.verify_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неправильний логін або пароль")
    return user

@app.post("/chat")
async def chat(req: ChatRequest):
    allowed_categories = iam_service.get_categories_for_role(req.role)
    if not allowed_categories:
        return {"answer": "У вашої ролі немає доступу до жодних документів."}
    answer = rag_service.run_rag_pipeline(req.query, allowed_categories)
    return {"answer": answer}

def verify_admin(role: str):
    if role != "Адмін":
        raise HTTPException(status_code=403, detail="Доступ заборонено: потрібні права адміністратора")

@app.get("/admin/users")
async def get_all_users(current_user_role: str):
    verify_admin(current_user_role)
    try:
        users = iam_service.get_all_users()
        if users is None:
            raise HTTPException(status_code=404, detail="Users list is empty or not found")
        return users    
    except Exception as e:
        print(f"Error fetching users: {str(e)}")

@app.get("/admin/roles")
async def get_all_roles(current_user_role: str):
    verify_admin(current_user_role)
    try:
        roles = iam_service.get_all_roles_with_permissions()
        if roles is None:
            raise HTTPException(status_code=404, detail="Roles list is empty or not found")
        return roles    
    except Exception as e:
        print(f"Error fetching roles: {str(e)}")

@app.post("/admin/add-role")
async def add_role(role: str, category: str, current_user_role: str = Query(...)):
    verify_admin(current_user_role)
    try:
        iam_service.add_new_role(role, category)
        return {"status": "success", "message": f"Роль {role} для категорії {category} додана"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/admin/delete-role")
async def add_role(role: str, category: str, current_user_role: str = Query(...)):
    verify_admin(current_user_role)
    try:
        iam_service.delete_role(role, category)
        return {"status": "success", "message": f"Доступ для категорії {category} видалено для ролі {role}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/admin/unique-roles")
async def get_unique_roles(current_user_role: str):
    verify_admin(current_user_role)
    try:
        unique_roles = iam_service.get_unique_roles()
        return unique_roles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/admin/unique-categories")
async def get_unique_categories(current_user_role: str):
    verify_admin(current_user_role)
    try:
        unique_categories = qdrant_service.get_unique_categories_from_qdrant()
        return unique_categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/admin/categories/{role_name}")
async def get_categories_for_role(role_name: str, current_user_role: str):
    verify_admin(current_user_role)
    try:
        categories_for_role = iam_service.get_categories_for_role(role_name)
        return categories_for_role
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/admin/add-user")
async def add_user(user_data: UserCreate, current_user_role: str = Query(...)):
    verify_admin(current_user_role)
    try:
        iam_service.add_new_user(
            user_data.username, 
            user_data.password, 
            user_data.role
        )
        return {"status": "success", "message": f"Користувача {user_data.username} додано"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Couldn`t create the user: {str(e)}")
    
@app.delete("/admin/delete-user/{username}")
async def delete_user(username: str, current_user_role: str = Query(...)):
    verify_admin(current_user_role)
    try:
        iam_service.delete_user(username)
        return {"status": "success", "message": f"Користувача {username} видалено"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Couldn`t delete the user: {str(e)}")
