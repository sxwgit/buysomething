import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'procurement-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'procurement.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'attachments')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB
    ADMIN_SESSION_HOURS = 2
