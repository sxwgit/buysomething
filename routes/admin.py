from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session, current_app

from models import AdminPassword, AdminUser, db

admin_bp = Blueprint('admin', __name__)


def ensure_admin_users():
    if AdminUser.query.first() is not None:
        # Ensure at least one root admin exists
        if not AdminUser.query.filter_by(is_root=True).first():
            first = AdminUser.query.order_by(AdminUser.id.asc()).first()
            if first:
                first.is_root = True
                db.session.commit()
        return

    legacy = AdminPassword.query.first()
    if legacy:
        admin_user = AdminUser(username='admin', is_root=True)
        admin_user.password_hash = legacy.password_hash
        db.session.add(admin_user)
        db.session.commit()


def current_admin_user():
    if 'is_admin' not in session:
        return None
    expire_str = session.get('admin_expire')
    if not expire_str:
        return None
    try:
        expire = datetime.fromisoformat(expire_str)
        if datetime.now() > expire:
            session.pop('is_admin', None)
            session.pop('admin_expire', None)
            session.pop('admin_user_id', None)
            session.pop('admin_username', None)
            return None
    except (ValueError, TypeError):
        return None

    admin_user = AdminUser.query.get(session.get('admin_user_id'))
    if not admin_user:
        session.pop('is_admin', None)
        session.pop('admin_expire', None)
        session.pop('admin_user_id', None)
        session.pop('admin_username', None)
        return None
    return admin_user


def is_admin():
    return current_admin_user() is not None


def is_root_admin():
    user = current_admin_user()
    return user is not None and user.is_root


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
        session['admin_expire'] = (datetime.now() + timedelta(hours=current_app.config.get('ADMIN_SESSION_HOURS', 2))).isoformat()
        return jsonify({'ok': True, 'username': admin.username, 'is_root': admin.is_root})
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
        'is_root': user.is_root if user else False,
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
def list_admin_users():
    if not is_root_admin():
        return jsonify({'msg': '需要根管理员权限'}), 403
    ensure_admin_users()
    users = AdminUser.query.order_by(AdminUser.id.asc()).all()
    return jsonify([u.to_dict() for u in users])


@admin_bp.route('/api/admin/users', methods=['POST'])
def create_admin_user():
    if not is_root_admin():
        return jsonify({'msg': '需要根管理员权限'}), 403
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
    if not is_root_admin():
        return jsonify({'msg': '需要根管理员权限'}), 403

    current_user = current_admin_user()
    if current_user and current_user.id == user_id:
        return jsonify({'msg': '不能删除当前登录的管理员'}), 400

    if AdminUser.query.filter(AdminUser.is_root == True).count() <= 1 and \
       AdminUser.query.get(user_id) and AdminUser.query.get(user_id).is_root:
        return jsonify({'msg': '系统至少需要保留一个根管理员'}), 400

    user = AdminUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/change-password', methods=['POST'])
def change_password():
    admin = current_admin_user()
    if not admin:
        return jsonify({'msg': '需要管理员权限'}), 403
    data = request.get_json() or {}
    old_pwd = data.get('old_password', '')
    new_pwd = data.get('new_password', '')
    if len(new_pwd) < 6:
        return jsonify({'msg': '新密码至少 6 位'}), 400
    if not admin.check_password(old_pwd):
        return jsonify({'msg': '当前密码错误'}), 400
    admin.set_password(new_pwd)
    db.session.commit()
    return jsonify({'ok': True})
