from flask import Flask, render_template
from sqlalchemy import text
from models import db
from config import Config
from routes.procurement import procurement_bp
from routes.attachment import attachment_bp
from routes.report import report_bp
from routes.admin import admin_bp, ensure_admin_users, is_admin
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
        ensure_admin_users()

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
        if not is_admin():
            return render_template('index.html', active_page='index')
        return render_template('settings.html', active_page='settings')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
