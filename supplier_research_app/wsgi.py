"""Entry point for the Supplier Research Flask application."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "seed-admin":
        from app.models import User, db
        with app.app_context():
            if not User.query.filter_by(username="admin").first():
                admin = User(username="admin")
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()
                print("Admin user created: admin / admin123")
            else:
                print("Admin user already exists.")
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
