from app import app, db
from models import User

with app.app_context():
    u = User(name="Test Admin", email="admin@test.com", role="Admin")
    u.set_password("admin123")
    db.session.add(u)
    db.session.commit()
    print("Admin user created successfully!")