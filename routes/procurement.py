from flask import Blueprint, request, jsonify
from models import db, Procurement
from routes.admin import is_admin

procurement_bp = Blueprint('procurement', __name__)


@procurement_bp.route('/api/procurements', methods=['GET'])
def list_procurements():
    query = Procurement.query.filter_by(is_deleted=0)

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    department = request.args.get('department')
    status = request.args.get('status')
    keyword = request.args.get('keyword')

    if year:
        query = query.filter_by(year=year)
    if month:
        query = query.filter_by(month=month)
    if department:
        query = query.filter_by(department=department)
    if status:
        query = query.filter_by(status=status)
    if keyword:
        kw = f'%{keyword}%'
        query = query.filter(
            db.or_(
                Procurement.item_name.like(kw),
                Procurement.requester_name.like(kw),
                Procurement.asset_code.like(kw),
                Procurement.manufacturer.like(kw),
            )
        )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = query.order_by(Procurement.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
    })


@procurement_bp.route('/api/procurements', methods=['POST'])
def create_procurement():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    data = request.get_json()
    p = Procurement(
        year=data['year'],
        month=data['month'],
        asset_category=data['asset_category'],
        item_name=data['item_name'],
        manufacturer=data.get('manufacturer', ''),
        model=data.get('model', ''),
        budget_qty=data['budget_qty'],
        unit_price=data['unit_price'],
        total_price=data['budget_qty'] * data['unit_price'],
        department=data['department'],
        requester_name=data['requester_name'],
        requester_id=data['requester_id'],
        asset_code=data.get('asset_code', ''),
        reason=data['reason'],
        remark=data.get('remark', ''),
        status=data.get('status', '已申请'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@procurement_bp.route('/api/procurements/<int:pid>', methods=['PUT'])
def update_procurement(pid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    p = Procurement.query.get_or_404(pid)
    data = request.get_json()
    for field in ['year', 'month', 'asset_category', 'item_name', 'manufacturer',
                  'model', 'budget_qty', 'unit_price', 'department',
                  'requester_name', 'requester_id', 'asset_code',
                  'reason', 'remark', 'status']:
        if field in data:
            setattr(p, field, data[field])
    if 'budget_qty' in data or 'unit_price' in data:
        p.total_price = p.budget_qty * p.unit_price
    db.session.commit()
    return jsonify(p.to_dict())


@procurement_bp.route('/api/procurements/<int:pid>', methods=['DELETE'])
def delete_procurement(pid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    p = Procurement.query.get_or_404(pid)
    p.is_deleted = 1
    db.session.commit()
    return jsonify({'ok': True})


@procurement_bp.route('/api/procurements/batch-status', methods=['POST'])
def batch_update_status():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    data = request.get_json()
    ids = data.get('ids', [])
    status = data.get('status')
    if not ids or not status:
        return jsonify({'msg': '参数不完整'}), 400
    Procurement.query.filter(Procurement.id.in_(ids)).update(
        {'status': status}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({'ok': True, 'updated': len(ids)})
