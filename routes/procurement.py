from datetime import datetime

from flask import Blueprint, request, jsonify
from sqlalchemy import case, func, or_
from models import db, Procurement
from routes.admin import is_admin

procurement_bp = Blueprint('procurement', __name__)


REQUIRED_FIELDS = [
    'year', 'month', 'asset_category', 'item_name', 'budget_qty',
    'unit_price', 'department', 'requester_name', 'requester_id', 'reason',
]


def validate_procurement_payload(data):
    missing = [field for field in REQUIRED_FIELDS if data.get(field) in (None, '', [])]
    if missing:
        return f"缺少必填字段: {', '.join(missing)}"

    if data.get('budget_qty', 0) <= 0:
        return '预算数量必须大于 0'

    if data.get('unit_price', -1) < 0:
        return '预计单价不能小于 0'

    month = data.get('month')
    if month is not None and not 1 <= month <= 12:
        return '采购月份必须在 1 到 12 之间'

    return None


def get_multi_values(args, key, cast=None):
    values = []
    raw_values = args.getlist(key) + args.getlist(f'{key}[]')
    if not raw_values and args.get(key):
        raw_values = [args.get(key)]

    for raw in raw_values:
        if raw is None:
            continue
        parts = [part.strip() for part in str(raw).split(',')]
        for part in parts:
            if not part:
                continue
            if cast:
                try:
                    values.append(cast(part))
                except (TypeError, ValueError):
                    continue
            else:
                values.append(part)

    # keep order while removing duplicates
    deduped = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def build_procurement_query(args):
    query = Procurement.query.filter_by(is_deleted=0)

    years = get_multi_values(args, 'year', int)
    months = get_multi_values(args, 'month', int)
    departments = get_multi_values(args, 'department')
    statuses = get_multi_values(args, 'status')
    keyword = (args.get('keyword') or '').strip()

    if years:
        query = query.filter(Procurement.year.in_(years))
    if months:
        query = query.filter(Procurement.month.in_(months))
    if departments:
        query = query.filter(Procurement.department.in_(departments))
    if statuses:
        query = query.filter(Procurement.status.in_(statuses))
    if keyword:
        terms = [term for term in keyword.split() if term]
        if not terms:
            terms = [keyword]

        searchable_fields = [
            Procurement.item_name,
            Procurement.requester_name,
            Procurement.requester_id,
            Procurement.asset_code,
            Procurement.manufacturer,
            Procurement.model,
            Procurement.reason,
            Procurement.remark,
            Procurement.department,
            Procurement.asset_category,
            Procurement.status,
        ]
        for term in terms:
            kw = f'%{term}%'
            query = query.filter(or_(*[field.like(kw) for field in searchable_fields]))

    return query


@procurement_bp.route('/api/procurements/filter-metadata', methods=['GET'])
def procurement_filter_metadata():
    current_year = datetime.now().year
    max_data_year = db.session.query(func.max(Procurement.year)).filter_by(is_deleted=0).scalar() or current_year
    upper_year = max(current_year, int(max_data_year))
    years = list(range(upper_year, 2021, -1))

    return jsonify({
        'years': years,
        'months': list(range(1, 13)),
    })


@procurement_bp.route('/api/procurements', methods=['GET'])
def list_procurements():
    query = build_procurement_query(request.args)
    query = query.order_by(Procurement.id.desc())

    if request.args.get('draw') is not None:
        draw = request.args.get('draw', 1, type=int)
        start = request.args.get('start', 0, type=int)
        length = request.args.get('length', 20, type=int)
        length = max(10, min(length, 100))
        page = start // length + 1
        total = Procurement.query.filter_by(is_deleted=0).count()
        filtered = query.count()
        pagination = query.paginate(page=page, per_page=length, error_out=False)
        return jsonify({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': filtered,
            'data': [p.to_dict() for p in pagination.items],
        })

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = max(1, min(per_page, 100))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
    })


@procurement_bp.route('/api/procurements/summary', methods=['GET'])
def procurement_summary():
    query = build_procurement_query(request.args)
    summary = query.with_entities(
        func.count(Procurement.id).label('total_count'),
        func.coalesce(func.sum(Procurement.total_price), 0).label('total_amount'),
        func.sum(case((Procurement.status != '已完成', 1), else_=0)).label('pending_count'),
        func.coalesce(func.sum(case((Procurement.status != '已完成', Procurement.total_price), else_=0)), 0).label('pending_amount'),
    ).first()

    return jsonify({
        'total_count': int(summary.total_count or 0),
        'total_amount': round(float(summary.total_amount or 0), 2),
        'pending_count': int(summary.pending_count or 0),
        'pending_amount': round(float(summary.pending_amount or 0), 2),
    })


@procurement_bp.route('/api/procurements/<int:pid>', methods=['GET'])
def get_procurement(pid):
    p = Procurement.query.filter_by(id=pid, is_deleted=0).first_or_404()
    return jsonify(p.to_dict())


@procurement_bp.route('/api/procurements', methods=['POST'])
def create_procurement():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403

    data = request.get_json() or {}
    err = validate_procurement_payload(data)
    if err:
        return jsonify({'msg': err}), 400

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
    p = Procurement.query.filter_by(id=pid, is_deleted=0).first_or_404()

    data = request.get_json() or {}
    for field in ['year', 'month', 'asset_category', 'item_name', 'manufacturer',
                  'model', 'budget_qty', 'unit_price', 'department',
                  'requester_name', 'requester_id', 'asset_code',
                  'reason', 'remark', 'status']:
        if field in data:
            setattr(p, field, data[field])

    err = validate_procurement_payload({
        'year': p.year,
        'month': p.month,
        'asset_category': p.asset_category,
        'item_name': p.item_name,
        'budget_qty': p.budget_qty,
        'unit_price': p.unit_price,
        'department': p.department,
        'requester_name': p.requester_name,
        'requester_id': p.requester_id,
        'reason': p.reason,
    })
    if err:
        return jsonify({'msg': err}), 400

    if 'budget_qty' in data or 'unit_price' in data:
        p.total_price = p.budget_qty * p.unit_price
    db.session.commit()
    return jsonify(p.to_dict())


@procurement_bp.route('/api/procurements/<int:pid>', methods=['DELETE'])
def delete_procurement(pid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    p = Procurement.query.filter_by(id=pid, is_deleted=0).first_or_404()
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
    Procurement.query.filter(Procurement.id.in_(ids), Procurement.is_deleted == 0).update(
        {'status': status}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({'ok': True, 'updated': len(ids)})
