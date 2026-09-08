import os
from functools import wraps
from flask import abort
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from . import config  # noqa: F401 - garanteix que .env s'ha carregat abans de llegir credencials

login_manager = LoginManager()
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, username, role='user'):
        self.id = username
        self.role = role

    @property
    def is_admin(self):
        return self.role == 'admin'


def _load_accounts():
    accounts = {}
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'canvia-aquesta-contrasenya')
    accounts[admin_username] = {
        'password_hash': generate_password_hash(admin_password),
        'role': 'admin',
    }

    user_username = os.getenv('USER_USERNAME')
    user_password = os.getenv('USER_PASSWORD')
    if user_username and user_password:
        accounts[user_username] = {
            'password_hash': generate_password_hash(user_password),
            'role': 'user',
        }

    return accounts


_ACCOUNTS = _load_accounts()


@login_manager.user_loader
def load_user(user_id):
    account = _ACCOUNTS.get(user_id)
    if account:
        return User(user_id, role=account['role'])
    return None


def verify_credentials(username, password):
    """Retorna el User si les credencials son valides, sino None."""
    account = _ACCOUNTS.get(username)
    if account and check_password_hash(account['password_hash'], password):
        return User(username, role=account['role'])
    return None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            abort(403)
        return view(*args, **kwargs)
    return wrapped
