# 1. 克隆仓库
git clone https://gitee.com/yourname/classhelper.git
cd classhelper

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python
>>> from app import db
>>> db.create_all()
>>> exit()

# 4. 启动应用
python app.py
# 访问 http://127.0.0.1:5000
# 默认教师账号：teacher / 123456 (需手动注册，或添加初始化脚本)
