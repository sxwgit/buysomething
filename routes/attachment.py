import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file
from models import db, Attachment
from routes.admin import is_admin

attachment_bp = Blueprint('attachment', __name__)


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

    # Group by department
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

    if not all([year, month, department]):
        return jsonify({'msg': '年月和部门不能为空'}), 400

    if file.filename == '':
        return jsonify({'msg': '文件名为空'}), 400

    # Save file
    ext = os.path.splitext(file.filename)[1]
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(year), f"{month:02d}", department)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, saved_name)
    file.save(save_path)
    file_size = os.path.getsize(save_path)

    att = Attachment(
        year=year, month=month, department=department,
        file_name=saved_name, original_name=file.filename, file_size=file_size,
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
