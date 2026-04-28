from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session

from models import AdminPassword, AdminUser, db

admin_bp = Blueprint('admin', __name__)


def ensure_admin_users():
    if AdminUser.query.first() is not None:
        return

    legacy = AdminPassword.query.first()
    if legacy:
        admin_user = AdminUser(username='admin')
        admin_user.password_hash = legacy.password_hash
        db.session.add(admin_user)
        db.session.commit()


def current_admin_user():
    if not is_admin():
        return None
    admin_user_id = session.get('admin_user_id')
    if not admin_user_id:
        return None
    return AdminUser.query.get(admin_user_id)


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
            session.pop('admin_user_id', None)
            session.pop('admin_username', None)
            return False
    except (ValueError, TypeError):
        return False

    admin_user = AdminUser.query.get(session.get('admin_user_id'))
    if not admin_user:
        session.pop('is_admin', None)
        session.pop('admin_expire', None)
        session.pop('admin_user_id', None)
        session.pop('admin_username', None)
        return False
    return True


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    ensure_admin_users()
    if request.method == 'GET':
        return render_template('admin_login.html')

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'ok': False, 'msg': '请输入用户名和密码'}), 400

    admin = AdminUser.query.filter_by(username=username).first()
    if admin and admin.check_password(password):
        session['is_admin'] = True
        session['admin_user_id'] = admin.id
        session['admin_username'] = admin.username
        session['admin_expire'] = (datetime.now() + timedelta(hours=2)).isoformat()
        return jsonify({'ok': True, 'username': admin.username})
    return jsonify({'ok': False, 'msg': '用户名或密码错误'}), 403


@admin_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.pop('is_admin', None)
    session.pop('admin_expire', None)
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    return jsonify({'ok': True})


@admin_bp.route('/admin/check')
def check():
    user = current_admin_user()
    return jsonify({
        'is_admin': bool(user),
        'username': user.username if user else '',
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
def list_admin_users():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    ensure_admin_users()
    users = AdminUser.query.order_by(AdminUser.id.asc()).all()
    return jsonify([u.to_dict() for u in users])


@admin_bp.route('/api/admin/users', methods=['POST'])
def create_admin_user():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    ensure_admin_users()

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'msg': '用户名和密码不能为空'}), 400
    if len(password) < 6:
        return jsonify({'msg': '密码至少 6 位'}), 400
    if AdminUser.query.filter_by(username=username).first():
        return jsonify({'msg': '管理员用户名已存在'}), 400

    user = AdminUser(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_admin_user(user_id):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403

    current_user = current_admin_user()
    if current_user and current_user.id == user_id:
        return jsonify({'msg': '不能删除当前登录的管理员'}), 400

    if AdminUser.query.count() <= 1:
        return jsonify({'msg': '系统至少需要保留一个管理员'}), 400

    user = AdminUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'ok': True})
