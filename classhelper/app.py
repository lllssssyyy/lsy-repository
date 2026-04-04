import os
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Assignment, Submission, SigninSession, SigninRecord

# 初始化
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------- 辅助函数 -------------------
def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'teacher':
            flash('只有教师可以访问此页面', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'student':
            flash('只有学生可以访问此页面', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ------------------- 主页 & 登录/注册 -------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'欢迎回来，{user.real_name}', 'success')
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        real_name = request.form.get('real_name')
        student_id = request.form.get('student_id') if role == 'student' else None

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            password=hashed_pw,
            role=role,
            real_name=real_name,
            student_id=student_id
        )
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'student':
        return render_template('dashboard_student.html')
    else:
        return render_template('dashboard_teacher.html')

# ------------------- 作业管理（教师） -------------------
@app.route('/teacher/assignments')
@login_required
@teacher_required
def teacher_assignments():
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).order_by(Assignment.created_at.desc()).all()
    return render_template('assignments.html', assignments=assignments, role='teacher')

@app.route('/teacher/create_assignment', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_assignment():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except:
            flash('截止时间格式错误', 'danger')
            return redirect(url_for('create_assignment'))
        new_assign = Assignment(
            title=title,
            description=description,
            deadline=deadline,
            teacher_id=current_user.id
        )
        db.session.add(new_assign)
        db.session.commit()
        flash('作业发布成功', 'success')
        return redirect(url_for('teacher_assignments'))
    return render_template('create_assignment.html')

@app.route('/teacher/assignment/<int:aid>/submissions')
@login_required
@teacher_required
def view_submissions(aid):
    assignment = Assignment.query.get_or_404(aid)
    if assignment.teacher_id != current_user.id:
        abort(403)
    submissions = Submission.query.filter_by(assignment_id=aid).all()
    return render_template('view_submissions.html', assignment=assignment, submissions=submissions)

@app.route('/teacher/grade/<int:sid>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_submission(sid):
    submission = Submission.query.get_or_404(sid)
    assignment = Assignment.query.get(submission.assignment_id)
    if assignment.teacher_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        try:
            grade = float(request.form.get('grade'))
            if 0 <= grade <= 100:
                submission.grade = grade
                db.session.commit()
                flash('评分成功', 'success')
            else:
                flash('分数应在0-100之间', 'danger')
        except:
            flash('请输入数字', 'danger')
        return redirect(url_for('view_submissions', aid=assignment.id))
    return render_template('grade_submission.html', submission=submission, assignment=assignment)

# ------------------- 作业提交（学生） -------------------
@app.route('/student/assignments')
@login_required
@student_required
def student_assignments():
    assignments = Assignment.query.order_by(Assignment.deadline).all()
    # 查询当前学生是否已提交
    submissions = Submission.query.filter_by(student_id=current_user.id).all()
    submitted_ids = [s.assignment_id for s in submissions]
    return render_template('assignments.html', assignments=assignments, role='student', submitted_ids=submitted_ids)

@app.route('/student/submit/<int:aid>', methods=['GET', 'POST'])
@login_required
@student_required
def submit_assignment(aid):
    assignment = Assignment.query.get_or_404(aid)
    # 检查是否已经提交
    existing = Submission.query.filter_by(student_id=current_user.id, assignment_id=aid).first()
    if existing:
        flash('你已经提交过该作业，不可重复提交', 'warning')
        return redirect(url_for('student_assignments'))
    if datetime.utcnow() > assignment.deadline:
        flash('作业已截止，无法提交', 'danger')
        return redirect(url_for('student_assignments'))

    if request.method == 'POST':
        content_text = request.form.get('content_text')
        file = request.files.get('file')
        file_path = None
        if file and file.filename:
            filename = secure_filename(f"{current_user.id}_{aid}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        sub = Submission(
            content_text=content_text,
            file_path=file_path,
            student_id=current_user.id,
            assignment_id=aid
        )
        db.session.add(sub)
        db.session.commit()
        flash('作业提交成功', 'success')
        return redirect(url_for('student_assignments'))
    return render_template('submit_assignment.html', assignment=assignment)

# ------------------- 签到功能 -------------------
@app.route('/teacher/start_signin', methods=['GET', 'POST'])
@login_required
@teacher_required
def start_signin():
    if request.method == 'POST':
        duration_min = int(request.form.get('duration', 10))
        code = ''.join(random.choices(string.digits, k=4))
        end_time = datetime.utcnow() + timedelta(minutes=duration_min)
        session = SigninSession(
            code=code,
            end_time=end_time,
            teacher_id=current_user.id
        )
        db.session.add(session)
        db.session.commit()
        flash(f'签到码: {code} (有效期{duration_min}分钟)', 'success')
        return redirect(url_for('dashboard'))
    return render_template('start_signin.html')

@app.route('/student/signin', methods=['GET', 'POST'])
@login_required
@student_required
def student_signin():
    if request.method == 'POST':
        code = request.form.get('code').strip()
        session = SigninSession.query.filter_by(code=code).first()
        if session and session.end_time > datetime.utcnow():
            # 检查是否已签到过该session
            existing = SigninRecord.query.filter_by(student_id=current_user.id, session_id=session.id).first()
            if existing:
                flash('你已在本场签到中签到过了', 'warning')
            else:
                record = SigninRecord(student_id=current_user.id, session_id=session.id)
                db.session.add(record)
                db.session.commit()
                flash('签到成功', 'success')
        else:
            flash('签到码无效或已过期', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('signin.html')

@app.route('/teacher/signin_records')
@login_required
@teacher_required
def signin_records():
    sessions = SigninSession.query.filter_by(teacher_id=current_user.id).order_by(SigninSession.start_time.desc()).all()
    records_by_session = {}
    for sess in sessions:
        records = SigninRecord.query.filter_by(session_id=sess.id).all()
        students = []
        for rec in records:
            stu = User.query.get(rec.student_id)
            students.append({'name': stu.real_name, 'time': rec.signin_time})
        records_by_session[sess.id] = students
    return render_template('signin_records.html', sessions=sessions, records_by_session=records_by_session)

# ------------------- 成绩统计（教师） -------------------
@app.route('/teacher/statistics')
@login_required
@teacher_required
def statistics():
    # 获取所有学生
    students = User.query.filter_by(role='student').all()
    student_scores = []
    for stu in students:
        subs = Submission.query.filter_by(student_id=stu.id).filter(Submission.grade.isnot(None)).all()
        if subs:
            total = sum(s.grade for s in subs)
            avg = total / len(subs)
        else:
            avg = 0
        student_scores.append({'name': stu.real_name, 'avg': avg})
    # 统计数据
    scores = [s['avg'] for s in student_scores]
    avg_score = sum(scores)/len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    bins = [0,0,0,0,0]
    for s in scores:
        if s < 60: bins[0]+=1
        elif s < 70: bins[1]+=1
        elif s < 80: bins[2]+=1
        elif s < 90: bins[3]+=1
        else: bins[4]+=1
    return render_template('statistics.html', 
                           avg_score=round(avg_score,1), 
                           max_score=round(max_score,1),
                           min_score=round(min_score,1),
                           bins=bins,
                           student_scores=student_scores)

# ------------------- 文件下载（教师查看学生作业） -------------------
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ------------------- 启动 -------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)