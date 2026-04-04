from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    # 检查是否已有教师账号
    if not User.query.filter_by(username='teacher').first():
        teacher = User(
            username='teacher',
            password=generate_password_hash('123456'),
            role='teacher',
            real_name='张老师',
            student_id=None
        )
        db.session.add(teacher)
    if not User.query.filter_by(username='student1').first():
        student1 = User(
            username='student1',
            password=generate_password_hash('123456'),
            role='student',
            real_name='张三',
            student_id='20240001'
        )
        db.session.add(student1)
    if not User.query.filter_by(username='student2').first():
        student2 = User(
            username='student2',
            password=generate_password_hash('123456'),
            role='student',
            real_name='李四',
            student_id='20240002'
        )
        db.session.add(student2)
    db.session.commit()
    print("数据库初始化完成，测试账号：teacher/123456, student1/123456, student2/123456")