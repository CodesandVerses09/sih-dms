from app import app, db
from models import User

with app.app_context():
    u = User(name="Test Investigator", email="test@test.com", role="Investigator")
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    print("User created successfully!")