import os

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User, Case, Document, Version, AuditLog
from werkzeug.utils import secure_filename
import hashlib
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dms.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists('uploads'):
    os.makedirs('uploads')

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class LoginUser(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.role = user.role
        self.name = user.name

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return LoginUser(user) if user else None

def log_action(action, document_id=None, case_id=None):
    log = AuditLog(user_id=current_user.id, action=action, document_id=document_id, case_id=case_id)
    db.session.add(log)
    db.session.commit()

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
    cases = Case.query.all()
    return render_template('dashboard.html', cases=cases, role=current_user.role, name=current_user.name)

@app.route('/case/new', methods=['GET', 'POST'])
@login_required
def new_case():
    if request.method == 'POST':
        case = Case(case_title=request.form['title'], case_number=request.form['number'], created_by=current_user.id)
        db.session.add(case)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('new_case.html')

@app.route('/case/<int:case_id>')
@login_required
def view_case(case_id):
    case = Case.query.get_or_404(case_id)
    documents = Document.query.filter_by(case_id=case_id).all()
    return render_template('case.html', case=case, documents=documents)

@app.route('/case/<int:case_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_document(case_id):
    if request.method == 'POST':
        file = request.files['file']
        title = request.form['title']
        doc_type = request.form['doc_type']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        doc = Document(case_id=case_id, title=title, document_type=doc_type, uploaded_by=current_user.id)
        db.session.add(doc)
        db.session.commit()

        version = Version(document_id=doc.id, file_path=filepath, version_number=1, file_hash=file_hash, uploaded_by=current_user.id)
        db.session.add(version)
        db.session.commit()

        log_action('UPLOAD', document_id=doc.id, case_id=case_id)
        return redirect(url_for('view_case', case_id=case_id))
    return render_template('upload.html', case_id=case_id)

@app.route('/document/<int:doc_id>/new_version', methods=['GET', 'POST'])
@login_required
def new_version(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        last_version = Version.query.filter_by(document_id=doc_id).order_by(Version.version_number.desc()).first()
        new_version_num = (last_version.version_number + 1) if last_version else 1

        version = Version(document_id=doc_id, file_path=filepath, version_number=new_version_num, file_hash=file_hash, uploaded_by=current_user.id)
        db.session.add(version)
        db.session.commit()

        log_action('NEW_VERSION', document_id=doc_id, case_id=doc.case_id)
        return redirect(url_for('view_case', case_id=doc.case_id))
    return render_template('upload.html', case_id=doc.case_id)

@app.route('/document/<int:doc_id>/versions')
@login_required
def view_versions(doc_id):
    doc = Document.query.get_or_404(doc_id)
    versions = Version.query.filter_by(document_id=doc_id).order_by(Version.version_number.desc()).all()
    log_action('VIEW', document_id=doc_id, case_id=doc.case_id)
    return render_template('versions.html', doc=doc, versions=versions)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    results = Document.query.filter(Document.title.contains(query)).all() if query else []
    return render_template('search.html', results=results, query=query)

@app.route('/audit-log')
@login_required
def audit_log():
    if current_user.role != 'Admin':
        return "Access Denied: Admins only", 403
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('audit_log.html', logs=logs)

@app.route('/admin-panel')
@login_required
def admin_panel():
    if current_user.role != 'Admin':
        return "Access Denied: Admins only", 403
    return "Welcome to the Admin Panel"

@app.route('/document/<int:doc_id>/toggle-redact')
@login_required
def toggle_redact(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if current_user.role == 'Admin':
        doc.is_redacted = not doc.is_redacted
        db.session.commit()
        log_action('REDACT_TOGGLE', document_id=doc_id, case_id=doc.case_id)
    return redirect(url_for('view_case', case_id=doc.case_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
@app.route('/')
def index():
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()

    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        app.run(host ='0.0.0.0', port=port)
