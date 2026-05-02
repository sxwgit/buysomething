from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def bump_data_version():
    row = DataVersion.query.first()
    if row:
        row.version = (row.version or 0) + 1
    else:
        row = DataVersion(version=1)
        db.session.add(row)
    db.session.commit()


def get_data_version():
    row = DataVersion.query.first()
    return row.version if row else 0


class Procurement(db.Model):
    __tablename__ = 'procurement'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    asset_category = db.Column(db.String(100), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    manufacturer = db.Column(db.String(200))
    model = db.Column(db.String(200))
    budget_qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    requester_name = db.Column(db.String(100), nullable=False)
    requester_id = db.Column(db.String(100), nullable=False)
    asset_code = db.Column(db.String(200))
    reason = db.Column(db.Text, nullable=False)
    remark = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default='已申请')
    is_deleted = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'asset_category': self.asset_category,
            'item_name': self.item_name,
            'manufacturer': self.manufacturer or '',
            'model': self.model or '',
            'budget_qty': self.budget_qty,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'department': self.department,
            'requester_name': self.requester_name,
            'requester_id': self.requester_id,
            'asset_code': self.asset_code or '',
            'reason': self.reason,
            'remark': self.remark or '',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else '',
        }


class Attachment(db.Model):
    __tablename__ = 'attachment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    file_name = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'department': self.department,
            'file_name': self.file_name,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M') if self.upload_time else '',
        }


class DropdownOption(db.Model):
    __tablename__ = 'dropdown_option'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'value': self.value,
            'sort_order': self.sort_order,
        }


class AdminPassword(db.Model):
    __tablename__ = 'admin_password'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    password_hash = db.Column(db.String(500), nullable=False)


class DataVersion(db.Model):
    __tablename__ = 'data_version'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AdminUser(db.Model):
    __tablename__ = 'admin_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(500), nullable=False)
    is_root = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_root': self.is_root,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }
