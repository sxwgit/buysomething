from flask import Blueprint, request, jsonify
from models import db, DropdownOption
from routes.admin import is_admin

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/options/<category>', methods=['GET'])
def get_options(category):
    options = DropdownOption.query.filter_by(category=category).order_by(DropdownOption.sort_order).all()
    return jsonify([o.to_dict() for o in options])


@settings_bp.route('/api/options', methods=['POST'])
def add_option():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    data = request.get_json()
    opt = DropdownOption(
        category=data['category'],
        value=data['value'],
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(opt)
    db.session.commit()
    return jsonify(opt.to_dict()), 201


@settings_bp.route('/api/options/<int:oid>', methods=['PUT'])
def update_option(oid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    opt = DropdownOption.query.get_or_404(oid)
    data = request.get_json()
    if 'value' in data:
        opt.value = data['value']
    if 'sort_order' in data:
        opt.sort_order = data['sort_order']
    db.session.commit()
    return jsonify(opt.to_dict())


@settings_bp.route('/api/options/<int:oid>', methods=['DELETE'])
def delete_option(oid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    opt = DropdownOption.query.get_or_404(oid)
    db.session.delete(opt)
    db.session.commit()
    return jsonify({'ok': True})
