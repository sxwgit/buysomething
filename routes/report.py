from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from models import db, Procurement
from sqlalchemy import func
from openpyxl import Workbook

report_bp = Blueprint('report', __name__)


@report_bp.route('/api/reports/department-summary')
def department_summary():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year:
        return jsonify({'msg': '请选择年份'}), 400

    query = db.session.query(
        Procurement.department,
        func.count(Procurement.id).label('count'),
        func.sum(Procurement.budget_qty).label('total_qty'),
        func.sum(Procurement.total_price).label('total_amount'),
    ).filter_by(is_deleted=0, year=year)

    if month:
        query = query.filter_by(month=month)

    results = query.group_by(Procurement.department).all()

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
    ).filter_by(is_deleted=0, year=year)

    if month:
        query = query.filter_by(month=month)

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
    ).filter_by(is_deleted=0, year=year)

    if month:
        query = query.filter_by(month=month)

    results = query.group_by(Procurement.asset_category).all()
    return jsonify([{
        'category': r.asset_category,
        'count': r.count,
        'total_qty': int(r.total_qty or 0),
        'total_amount': round(float(r.total_amount or 0), 2),
    } for r in results])


@report_bp.route('/api/reports/export')
def export_excel():
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
        ).filter_by(is_deleted=0, year=year)
        if month:
            query = query.filter_by(month=month)
        for r in query.group_by(Procurement.department).all():
            ws.append([r.department, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])

    elif report_type == 'category-distribution':
        ws.title = '资产分类分布'
        ws.append(['资产分类', '记录条数', '采购总数', '采购总金额'])
        query = db.session.query(
            Procurement.asset_category,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.budget_qty).label('total_qty'),
            func.sum(Procurement.total_price).label('total_amount'),
        ).filter_by(is_deleted=0, year=year)
        if month:
            query = query.filter_by(month=month)
        for r in query.group_by(Procurement.asset_category).all():
            ws.append([r.asset_category, r.count, int(r.total_qty or 0), round(float(r.total_amount or 0), 2)])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"{period}_{report_type}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
