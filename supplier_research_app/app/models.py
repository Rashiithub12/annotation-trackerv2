"""SQLAlchemy database models."""
import bcrypt
from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    companies = db.relationship("Company", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company_name = db.Column(db.String(255))
    website = db.Column(db.String(500), nullable=False)
    generic_email = db.Column(db.String(255))
    email_source_url = db.Column(db.String(500))
    brands = db.Column(db.Text)
    brands_source_url = db.Column(db.String(500))
    brand_categories = db.Column(db.String(255))
    duplicate = db.Column(db.String(10), default="No")
    marketplace = db.Column(db.String(10), default="No")
    status = db.Column(db.String(50), default="pending")  # pending, completed, failed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name or "",
            "website": self.website,
            "generic_email": self.generic_email or "",
            "email_source_url": self.email_source_url or "",
            "brands": self.brands or "",
            "brands_source_url": self.brands_source_url or "",
            "brand_categories": self.brand_categories or "",
            "duplicate": self.duplicate or "No",
            "marketplace": self.marketplace or "No",
            "status": self.status,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
