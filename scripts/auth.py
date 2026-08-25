import os
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

login_manager = LoginManager()
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, username):
        self.id = username


def _load_admin_credentials():
    username = os.getenv('ADMIN_USERNAME', 'admin')
    password = os.getenv('ADMIN_PASSWORD', 'canvia-aquesta-contrasenya')
    return username, generate_password_hash(password)


_ADMIN_USERNAME, _ADMIN_PASSWORD_HASH = _load_admin_credentials()


@login_manager.user_loader
def load_user(user_id):
    if user_id == _ADMIN_USERNAME:
        return User(user_id)
    return None


def verify_credentials(username, password):
    return username == _ADMIN_USERNAME and check_password_hash(_ADMIN_PASSWORD_HASH, password)
