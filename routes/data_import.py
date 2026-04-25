import re
from flask import Blueprint, request, jsonify
from models import db, Procurement
from routes.admin import is_admin
from openpyxl import load_workbook

data_import_bp = Blueprint('data_import', __name__)

COLUMN_MAP = {
    '采购年份': 'year',
    '采购月份': 'month',
    '资产最小分类': 'asset_category',
    '物品名称': 'item_name',
    '生产厂家': 'manufacturer',
    '物品型号': 'model',
    '预算数量': 'budget_qty',
    '预计单价': 'unit_price',
    '总价': 'total_price',
    '需求部门': 'department',
    '需求人姓名': 'requester_name',
    '需求人工号': 'requester_id',
    '资产编码': 'asset_code',
    '申请原因': 'reason',
    '备注': 'remark',
    '采购状态': 'status',
}

REQUIRED_FIELDS = ['year', 'month', 'asset_category', 'item_name', 'budget_qty',
                   'unit_price', 'department', 'requester_name', 'requester_id', 'reason']


@data_import_bp.route('/api/import/excel', methods=['POST'])
def import_excel():
    if not is_admin():
        return jsonify({'msg': '需要管理员权限'}), 403

    if 'file' not in request.files:
        return jsonify({'msg': '未找到文件'}), 400

    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'msg': '仅支持 .xlsx 格式'}), 400

    try:
        wb = load_workbook(file, read_only=True)
        ws = wb.active

        # Read header row
        headers = []
        for cell in next(ws.iter_rows(min_row=1, max_row=1)):
            headers.append(str(cell.value).strip() if cell.value else '')

        # Map column index to field name
        col_map = {}
        for i, h in enumerate(headers):
            if h in COLUMN_MAP:
                col_map[i] = COLUMN_MAP[h]

        if not col_map:
            return jsonify({'msg': '未匹配到有效列名，请检查 Excel 表头'}), 400

        imported = 0
        errors = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            record = {}
            for col_idx, field in col_map.items():
                val = row[col_idx].value if col_idx < len(row) else None
                if val is not None:
                    val = str(val).strip()
                    if val == '' or val == 'None':
                        val = None
                record[field] = val

            # Parse year with flexible format
            if record.get('year'):
                year_str = str(record['year']).replace('年', '').strip()
                try:
                    record['year'] = int(float(year_str))
                except (ValueError, TypeError):
                    record['year'] = None

            if record.get('month'):
                month_str = str(record['month']).replace('月', '').strip()
                try:
                    record['month'] = int(float(month_str))
                except (ValueError, TypeError):
                    record['month'] = None

            # Parse numbers
            for num_field in ['budget_qty', 'unit_price', 'total_price']:
                if record.get(num_field):
                    try:
                        record[num_field] = float(record[num_field])
                        if num_field == 'budget_qty':
                            record[num_field] = int(record[num_field])
                    except (ValueError, TypeError):
                        record[num_field] = None

            # Check required fields
            missing = [f for f in REQUIRED_FIELDS if record.get(f) is None]
            if missing:
                errors.append(f"第 {row_idx} 行缺少必填字段: {', '.join(missing)}")
                continue

            # Calculate total_price
            if record.get('budget_qty') and record.get('unit_price'):
                record['total_price'] = record['budget_qty'] * record['unit_price']

            # Set defaults
            record.setdefault('status', '已申请')
            record.setdefault('manufacturer', '')
            record.setdefault('model', '')
            record.setdefault('asset_code', '')
            record.setdefault('remark', '')

            p = Procurement(**record)
            db.session.add(p)
            imported += 1

        db.session.commit()
        wb.close()

        return jsonify({
            'imported': imported,
            'errors': errors[:20],  # Limit error messages
            'total_errors': len(errors),
        })

    except Exception as e:
        return jsonify({'msg': f'导入失败: {str(e)}'}), 500
