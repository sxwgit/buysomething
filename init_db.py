"""Initialize database with default data."""
import os
import sys
from getpass import getpass

from flask import Flask
from models import db, DropdownOption, AdminPassword
from config import Config


DEFAULT_CATEGORIES = ['办公设备', '电子设备', '网络设备', '软件许可', '实验设备', '办公家具', '其他']
DEFAULT_DEPARTMENTS = ['研发部', '测试部', '产品部', '运维部', '行政部', '财务部']
DEFAULT_STATUSES = ['已申请', '采购中', '已完成']


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def init():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Seed dropdown options if empty
        if DropdownOption.query.first() is None:
            for i, val in enumerate(DEFAULT_CATEGORIES):
                db.session.add(DropdownOption(category='asset_category', value=val, sort_order=i))
            for i, val in enumerate(DEFAULT_DEPARTMENTS):
                db.session.add(DropdownOption(category='department', value=val, sort_order=i))
            for i, val in enumerate(DEFAULT_STATUSES):
                db.session.add(DropdownOption(category='status', value=val, sort_order=i))
            db.session.commit()
            print('Default dropdown options seeded.')

        # Set admin password if not set
        if AdminPassword.query.first() is None:
            if len(sys.argv) > 1:
                password = sys.argv[1]
            else:
                password = getpass('Set admin password (press Enter for "admin123"): ')
                password = password or 'admin123'
            admin = AdminPassword()
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f'Admin password set.')
        else:
            print('Admin password already exists.')

        # Ensure upload directory exists
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        print('Database initialized successfully.')


if __name__ == '__main__':
    init()
