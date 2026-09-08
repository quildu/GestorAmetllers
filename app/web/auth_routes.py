from flask import redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from ..auth import verify_credentials


def register(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            user = verify_credentials(username, password)
            if user:
                login_user(user)
                return redirect(request.args.get('next') or url_for('list_parcels'))
            return render_template('login.html', error='Usuari o contrasenya incorrectes')
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('login'))
