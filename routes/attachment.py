import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file
from models import db, Attachment, DropdownOption
from routes.admin import is_admin

attachment_bp = Blueprint('attachment', __name__)

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.msg', '.eml',
                      '.zip', '.rar', '.7z', '.png', '.jpg', '.jpeg', '.gif',
                      '.ppt', '.pptx', '.txt', '.csv', '.wps'}


@attachment_bp.route('/api/attachments', methods=['GET'])
def list_attachments():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    department = request.args.get('department')

    query = Attachment.query
    if year:
        query = query.filter_by(year=year)
    if month:
        query = query.filter_by(month=month)
    if department:
        query = query.filter_by(department=department)

    attachments = query.order_by(Attachment.upload_time.desc()).all()

    grouped = {}
    for a in attachments:
        key = f"{a.year}-{a.month:02d}-{a.department}"
        if key not in grouped:
            grouped[key] = {
                'year': a.year,
                'month': a.month,
                'department': a.department,
                'count': 0,
                'files': [],
            }
        grouped[key]['count'] += 1
        grouped[key]['files'].append(a.to_dict())

    return jsonify(list(grouped.values()))


@attachment_bp.route('/api/attachments/coverage', methods=['GET'])
def attachment_coverage():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'msg': '请选择年份和月份'}), 400

    departments = DropdownOption.query.filter_by(category='department') \
        .order_by(DropdownOption.sort_order, DropdownOption.id).all()
    dept_names = [d.value for d in departments]

    counts = db.session.query(
        Attachment.department,
        db.func.count(Attachment.id).label('file_count')
    ).filter_by(year=year, month=month).group_by(Attachment.department).all()
    count_map = {item.department: int(item.file_count or 0) for item in counts}

    coverage = [{
        'department': dept,
        'uploaded': count_map.get(dept, 0) > 0,
        'file_count': count_map.get(dept, 0),
    } for dept in dept_names]

    return jsonify({
        'year': year,
        'month': month,
        'total_departments': len(coverage),
        'uploaded_departments': sum(1 for item in coverage if item['uploaded']),
        'missing_departments': sum(1 for item in coverage if not item['uploaded']),
        'items': coverage,
    })


@attachment_bp.route('/api/attachments/upload', methods=['POST'])
def upload_attachment():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403

    if 'file' not in request.files:
        return jsonify({'msg': '未找到文件'}), 400

    file = request.files['file']
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    department = request.form.get('department')
    description = (request.form.get('description') or '').strip()

    if not all([year, month, department]):
        return jsonify({'msg': '年月和部门不能为空'}), 400

    if '/' in department or '\\' in department or '..' in department:
        return jsonify({'msg': '部门名称不合法'}), 400

    if file.filename == '':
        return jsonify({'msg': '文件名为空'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'msg': f'不支持的文件类型: {ext}'}), 400

    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(year), f"{month:02d}", department)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, saved_name)
    file.save(save_path)
    file_size = os.path.getsize(save_path)

    att = Attachment(
        year=year, month=month, department=department,
        file_name=saved_name, original_name=file.filename,
        file_size=file_size, description=description,
    )
    db.session.add(att)
    db.session.commit()
    return jsonify(att.to_dict()), 201


@attachment_bp.route('/api/attachments/<int:aid>/download')
def download_attachment(aid):
    att = Attachment.query.get_or_404(aid)
    file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        str(att.year), f"{att.month:02d}", att.department, att.file_name,
    )
    if not os.path.exists(file_path):
        return jsonify({'msg': '文件不存在'}), 404
    return send_file(file_path, as_attachment=True, download_name=att.original_name)


@attachment_bp.route('/api/attachments/<int:aid>', methods=['DELETE'])
def delete_attachment(aid):
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403
    att = Attachment.query.get_or_404(aid)
    file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        str(att.year), f"{att.month:02d}", att.department, att.file_name,
    )
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(att)
    db.session.commit()
    return jsonify({'ok': True})
