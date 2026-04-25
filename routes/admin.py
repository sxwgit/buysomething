from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session
from models import db, AdminPassword

admin_bp = Blueprint('admin', __name__)


def is_admin():
    if 'is_admin' not in session:
        return False
    expire_str = session.get('admin_expire')
    if not expire_str:
        return False
    try:
        expire = datetime.fromisoformat(expire_str)
        if datetime.now() > expire:
            session.pop('is_admin', None)
            session.pop('admin_expire', None)
            return False
    except (ValueError, TypeError):
        return False
    return True


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('admin_login.html')
    data = request.get_json() or {}
    password = data.get('password', '')
    admin = AdminPassword.query.first()
    if admin and admin.check_password(password):
        session['is_admin'] = True
        session['admin_expire'] = (datetime.now() + timedelta(hours=2)).isoformat()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': '密码错误'}), 403


@admin_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.pop('is_admin', None)
    session.pop('admin_expire', None)
    return jsonify({'ok': True})


@admin_bp.route('/admin/check')
def check():
    return jsonify({'is_admin': is_admin()})
