import hashlib
from core.domain import User

# Простая "база данных" пользователей
users_db = [
    User(id="1", username="admin", password=hashlib.sha256("admin123".encode()).hexdigest(), role="admin"),
    User(id="2", username="user", password=hashlib.sha256("user123".encode()).hexdigest(), role="user")
]

def authenticate_user(username: str, password: str) -> User | None:
    """Аутентификация пользователя"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    for user in users_db:
        if user.username == username and user.password == hashed_password:
            return user
    return None

def is_admin(user: User) -> bool:
    """Проверка роли администратора"""
    return user.role == "admin"
