from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dms.db'

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class LoginUser(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.role = user.role

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return LoginUser(user) if user else None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(LoginUser(user))
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid email or password")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return f"Logged in! Your role: {current_user.role}"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)