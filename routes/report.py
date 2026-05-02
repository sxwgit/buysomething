from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from models import db, Procurement
from sqlalchemy import func, case
from openpyxl import Workbook

from routes.admin import is_admin

report_bp = Blueprint('report', __name__)


def build_base_query(year, month=None):
    query = Procurement.query.filter_by(is_deleted=0, year=year)
    if month:
        query = query.filter_by(month=month)
    return query


@report_bp.route('/api/reports/department-summary')
def department_summary():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(year, month)
    results = db.session.query(
        Procurement.department,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.budget_qty).label('total_qty'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(base.with_entities(Procurement.id))).group_by(Procurement.department).all()

    return jsonify([{
        'department': r.department,
        'count': r.count,
        'total_qty': int(r.total_qty or 0),
        'total_amount': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/department-ratio')
def department_ratio():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    query = db.session.query(
        Procurement.department,
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(build_base_query(year, month).with_entities(Procurement.id)))

    results = query.group_by(Procurement.department).all()
    return jsonify([{
        'name': r.department,
        'value': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/category-distribution')
def category_distribution():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    query = db.session.query(
        Procurement.asset_category,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.budget_qty).label('total_qty'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter(Procurement.id.in_(build_base_query(year, month).with_entities(Procurement.id)))

    results = query.group_by(Procurement.asset_category).all()
    return jsonify([{
        'category': r.asset_category,
        'count': r.count,
        'total_qty': int(r.total_qty or 0),
        'total_amount': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/overview')
def procurement_overview():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    base = build_base_query(year, month)
    base_ids = base.with_entities(Procurement.id)

    # Aggregate stats in one SQL query
    stats = db.session.query(
        func.count(Procurement.id).label('total_count'),
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
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    wb = Workbook()
    ws = wb.active
    period = f"{year}年" + (f"{month}月" if month else "全年")

    if report_type == 'department-summary':
        ws.title = '部门采购汇总'
        ws.append(['部门', '记录条数', '采购总数', '采购总金额'])
        query = db.session.query(
            Procurement.department,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.budget_qty).label('total_qty'),
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter(Procurement.id.in_(build_base_query(year, month).with_entities(Procurement.id)))
        for r in query.group_by(Procurement.department).all():
            ws.append([r.department, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])

    elif report_type == 'department-ratio':
        ws.title = '部门金额占比'
        ws.append(['部门', '采购总金额', '金额占比'])
        query = db.session.query(
            Procurement.department,
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter(Procurement.id.in_(build_base_query(year, month).with_entities(Procurement.id)))
        rows = query.group_by(Procurement.department).all()
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
        ).filter(Procurement.id.in_(build_base_query(year, month).with_entities(Procurement.id)))
        for r in query.group_by(Procurement.asset_category).all():
            ws.append([r.asset_category, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])
    else:
        return jsonify({'msg': '不支持的报表类型'}), 400

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"{period}_{report_type}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
