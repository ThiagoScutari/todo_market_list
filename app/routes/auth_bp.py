from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.core import User

# Cria o Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, manda para o dashboard
    if current_user.is_authenticated: 
        return redirect(url_for('main.dashboard')) # Note: main.dashboard
    
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        # Busca o usuário
        user = User.query.filter(User.username.ilike(u.strip())).first()
        
        if user and user.check_password(p):
            login_user(user, remember=True)
            return redirect(url_for('main.dashboard'))
        
        flash('Usuário ou senha incorretos', 'error')
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))