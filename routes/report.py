from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from models import db, Procurement
from sqlalchemy import func, case
from openpyxl import Workbook

from routes.admin import is_admin

report_bp = Blueprint('report', __name__)


def get_multi_values(args, key, cast=None):
    values = []
    raw_values = args.getlist(key) + args.getlist(f'{key}[]')
    if not raw_values and args.get(key):
        raw_values = [args.get(key)]

    for raw in raw_values:
        if raw is None:
            continue
        for part in [item.strip() for item in str(raw).split(',')]:
            if not part:
                continue
            if cast:
                try:
                    values.append(cast(part))
                except (TypeError, ValueError):
                    continue
            else:
                values.append(part)

    deduped = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def get_report_filters():
    years = get_multi_values(request.args, 'year', int)
    return {
        'year': years[0] if years else None,
        'months': get_multi_values(request.args, 'month', int),
        'departments': get_multi_values(request.args, 'department'),
        'categories': get_multi_values(request.args, 'asset_category'),
    }


def build_base_query(year, months=None, departments=None, categories=None):
    query = Procurement.query.filter_by(is_deleted=0, year=year)
    if months:
        query = query.filter(Procurement.month.in_(months))
    if departments:
        query = query.filter(Procurement.department.in_(departments))
    if categories:
        query = query.filter(Procurement.asset_category.in_(categories))
    return query


@report_bp.route('/api/reports/department-summary')
def department_summary():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(**filters)
    results = db.session.query(
        Procurement.department,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.budget_qty).label('total_qty'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(base.with_entities(Procurement.id))) \
        .group_by(Procurement.department) \
        .order_by(func.sum(Procurement.total_price).desc()) \
        .all()

    return jsonify([{
        'department': r.department,
        'count': r.count,
        'total_qty': int(r.total_qty or 0),
        'total_amount': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/department-ratio')
def department_ratio():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    query = db.session.query(
        Procurement.department,
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(build_base_query(**filters).with_entities(Procurement.id)))

    results = query.group_by(Procurement.department).order_by(func.sum(Procurement.total_price).desc()).all()
    return jsonify([{
        'name': r.department,
        'value': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/category-distribution')
def category_distribution():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    query = db.session.query(
        Procurement.asset_category,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.budget_qty).label('total_qty'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(build_base_query(**filters).with_entities(Procurement.id)))

    results = query.group_by(Procurement.asset_category).order_by(func.sum(Procurement.total_price).desc()).all()
    return jsonify([{
        'category': r.asset_category,
        'count': r.count,
        'total_qty': int(r.total_qty or 0),
        'total_amount': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/department-category-matrix')
def department_category_matrix():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(**filters)
    rows = db.session.query(
        Procurement.department,
        Procurement.asset_category,
        func.count(Procurement.id).label('count'),
        func.coalesce(func.sum(Procurement.budget_qty), 0).label('total_qty'),
        func.coalesce(func.sum(Procurement.total_price), 0).label('total_amount'),
    ).filter(Procurement.id.in_(base.with_entities(Procurement.id))) \
        .group_by(Procurement.department, Procurement.asset_category) \
        .all()

    category_totals = {}
    department_map = {}
    for row in rows:
        category = row.asset_category or '未分类'
        department = row.department or '未填写部门'
        amount = round(float(row.total_amount or 0), 2)
        cell = {
            'count': int(row.count or 0),
            'total_qty': int(row.total_qty or 0),
            'total_amount': amount,
        }

        category_totals[category] = category_totals.get(category, 0) + amount
        dept = department_map.setdefault(department, {
            'department': department,
            'total_count': 0,
            'total_qty': 0,
            'total_amount': 0,
            'cells': {},
        })
        dept['total_count'] += cell['count']
        dept['total_qty'] += cell['total_qty']
        dept['total_amount'] = round(dept['total_amount'] + amount, 2)
        dept['cells'][category] = cell

    if filters['categories']:
        categories = filters['categories']
    else:
        categories = [name for name, _ in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)]

    matrix_rows = sorted(department_map.values(), key=lambda item: item['total_amount'], reverse=True)
    return jsonify({
        'categories': categories,
        'rows': matrix_rows,
    })


@report_bp.route('/api/reports/monthly-trend')
def monthly_trend():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(**filters)
    rows = db.session.query(
        Procurement.month,
        func.count(Procurement.id).label('count'),
        func.coalesce(func.sum(Procurement.budget_qty), 0).label('total_qty'),
        func.coalesce(func.sum(Procurement.total_price), 0).label('total_amount'),
        func.coalesce(func.sum(case((Procurement.status != '已完成', Procurement.total_price), else_=0)), 0).label('pending_amount'),
    ).filter(Procurement.id.in_(base.with_entities(Procurement.id))) \
        .group_by(Procurement.month) \
        .order_by(Procurement.month.asc()) \
        .all()

    row_map = {row.month: row for row in rows}
    month_scope = filters['months'] or list(range(1, 13))
    return jsonify([{
        'month': month,
        'count': int(row_map[month].count or 0) if month in row_map else 0,
        'total_qty': int(row_map[month].total_qty or 0) if month in row_map else 0,
        'total_amount': round(float(row_map[month].total_amount or 0), 2) if month in row_map else 0,
        'pending_amount': round(float(row_map[month].pending_amount or 0), 2) if month in row_map else 0,
    } for month in month_scope])


@report_bp.route('/api/reports/overview')
def procurement_overview():
    filters = get_report_filters()
    if not filters['year']:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(**filters)
    base_ids = base.with_entities(Procurement.id)

    # Aggregate stats in one SQL query
    stats = db.session.query(
        func.count(Procurement.id).label('total_count'),
        func.coalesce(func.sum(Procurement.budget_qty), 0).label('total_qty'),
        func.coalesce(func.sum(Procurement.total_price), 0).label('total_amount'),
        func.sum(case((Procurement.status != '已完成', 1), else_=0)).label('pending_count'),
        func.coalesce(func.sum(case((Procurement.status != '已完成', Procurement.total_price), else_=0)), 0).label('pending_amount'),
    ).filter(Procurement.id.in_(base_ids)).first()

    # Status breakdown
    status_rows = db.session.query(
        Procurement.status,
        func.count(Procurement.id).label('count'),
        func.coalesce(func.sum(Procurement.total_price), 0).label('amount'),
    ).filter(Procurement.id.in_(base_ids)).group_by(Procurement.status).all()

    status_map = {r.status: {'count': int(r.count), 'amount': round(float(r.amount or 0), 2)} for r in status_rows}
    status_summary = []
    for status in ['已申请', '采购中', '已完成']:
        info = status_map.get(status, {'count': 0, 'amount': 0.0})
        status_summary.append({'status': status, 'count': info['count'], 'amount': info['amount']})

    # Top department
    top_department = db.session.query(
        Procurement.department,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(base_ids)) \
        .group_by(Procurement.department) \
        .order_by(func.sum(Procurement.total_price).desc()) \
        .first()

    top_record = base.order_by(Procurement.total_price.desc()).first()

    return jsonify({
        'total_count': int(stats.total_count or 0),
        'total_qty': int(stats.total_qty or 0),
        'total_amount': round(float(stats.total_amount or 0), 2),
        'pending_count': int(stats.pending_count or 0),
        'pending_amount': round(float(stats.pending_amount or 0), 2),
        'status_summary': status_summary,
        'top_department': {
            'department': top_department.department,
            'count': int(top_department.count or 0),
            'amount': round(float(top_department.total_amount or 0), 2),
        } if top_department else None,
        'top_record': {
            'item_name': top_record.item_name,
            'department': top_record.department,
            'amount': round(float(top_record.total_price or 0), 2),
            'status': top_record.status,
        } if top_record else None,
    })


@report_bp.route('/api/reports/export')
def export_excel():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    report_type = request.args.get('type', 'department-summary')
    filters = get_report_filters()
    year = filters['year']

    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    wb = Workbook()
    ws = wb.active
    period = f"{year}年" + (f"{','.join(map(str, filters['months']))}月" if filters['months'] else "全年")
    base_ids = build_base_query(**filters).with_entities(Procurement.id)

    if report_type == 'department-summary':
        ws.title = '部门采购汇总'
        ws.append(['部门', '记录条数', '采购总数', '采购总金额'])
        query = db.session.query(
            Procurement.department,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.budget_qty).label('total_qty'),
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter(Procurement.id.in_(base_ids))
        for r in query.group_by(Procurement.department).order_by(func.sum(Procurement.total_price).desc()).all():
            ws.append([r.department, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])

    elif report_type == 'department-ratio':
        ws.title = '部门金额占比'
        ws.append(['部门', '采购总金额', '金额占比'])
        query = db.session.query(
            Procurement.department,
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter(Procurement.id.in_(base_ids))
        rows = query.group_by(Procurement.department).order_by(func.sum(Procurement.total_price).desc()).all()
        total_amount = sum(float(r.total_amount or 0) for r in rows)
        for r in rows:
            amount = round(float(r.total_amount or 0), 2)
            ratio = f"{(amount / total_amount * 100):.2f}%" if total_amount else '0.00%'
            ws.append([r.department, amount, ratio])

    elif report_type == 'category-distribution':
        ws.title = '资产分类分布'
        ws.append(['资产分类', '记录条数', '采购总数', '采购总金额'])
        query = db.session.query(
            Procurement.asset_category,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.budget_qty).label('total_qty'),
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter(Procurement.id.in_(base_ids))
        for r in query.group_by(Procurement.asset_category).order_by(func.sum(Procurement.total_price).desc()).all():
            ws.append([r.asset_category, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])
    elif report_type == 'department-category-matrix':
        ws.title = '部门种类交叉分析'
        rows = db.session.query(
            Procurement.department,
            Procurement.asset_category,
            func.coalesce(func.sum(Procurement.total_price), 0).label('total_amount'),
        ).filter(Procurement.id.in_(base_ids)) \
            .group_by(Procurement.department, Procurement.asset_category) \
            .all()
        categories = filters['categories'] or sorted({row.asset_category for row in rows})
        departments = sorted({row.department for row in rows})
        value_map = {(row.department, row.asset_category): round(float(row.total_amount or 0), 2) for row in rows}
        ws.append(['部门', *categories, '合计'])
        for department in departments:
            values = [value_map.get((department, category), 0) for category in categories]
            ws.append([department, *values, round(sum(values), 2)])
    else:
        return jsonify({'msg': '不支持的报表类型'}), 400

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"{period}_{report_type}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
