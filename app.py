from flask import Flask, render_template, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text
from models import AdminPassword, AdminUser, db
from config import Config
from routes.procurement import procurement_bp
from routes.attachment import attachment_bp
from routes.report import report_bp
from routes.admin import admin_bp
from routes.settings import settings_bp
from routes.data_import import data_import_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    app.register_blueprint(procurement_bp)
    app.register_blueprint(attachment_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(data_import_bp)

    with app.app_context():
        db.create_all()

        if AdminUser.query.first() is None:
            legacy = AdminPassword.query.first()
            if legacy:
                admin_user = AdminUser(username='admin')
                admin_user.password_hash = legacy.password_hash
                db.session.add(admin_user)
                db.session.commit()

        db.session.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_procurement_year_month ON procurement(year, month)'
        ))
        db.session.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_procurement_department_status ON procurement(department, status)'
        ))
        db.session.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_procurement_item_name ON procurement(item_name)'
        ))
        db.session.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_attachment_year_month_department ON attachment(year, month, department)'
        ))
        db.session.commit()

    @app.route('/')
    def index():
        return render_template('index.html', active_page='index')

    @app.route('/attachments')
    def attachments():
        return render_template('attachments.html', active_page='attachments')

    @app.route('/reports')
    def reports():
        return render_template('reports.html', active_page='reports')

    @app.route('/settings')
    def settings():
        return render_template('settings.html', active_page='settings')

    @app.route('/api/admin/change-password', methods=['POST'])
    def change_password():
        from routes.admin import current_admin_user, is_admin
        if not is_admin():
            return jsonify({'msg': '需要管理员权限'}), 403
        data = request.get_json() or {}
        old_pwd = data.get('old_password', '')
        new_pwd = data.get('new_password', '')
        if len(new_pwd) < 6:
            return jsonify({'msg': '新密码至少 6 位'}), 400
        admin = current_admin_user()
        if not admin or not admin.check_password(old_pwd):
            return jsonify({'msg': '当前密码错误'}), 400
        admin.set_password(new_pwd)
        db.session.commit()
        return jsonify({'ok': True})

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
