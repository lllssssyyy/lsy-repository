# 课堂助手系统

ClassHelper 是一个轻量级的课堂管理 Web 应用，旨在帮助教师和学生高效地管理作业、签到和成绩。

# 简要介绍

这是一个课堂助手系统，主要实现以下功能： 用户认证、角色区分：学生和教师、作业管理：教师发布作业；学生提交作业；教师查看提交并评分、签到、 成绩分析：根据作业评分计算每个学生的总分，展示班级平均分、分数段分布（柱状图）、个人成绩对比等。

# 功能特性

作业管理：教师可以发布、评分作业；学生可以在线提交。
上课签到：教师可生成限时签到码，学生输入即可完成签到。
成绩分析：自动统计班级成绩，生成可视化图表。
角色区分：教师和学生拥有独立的操作界面。

# 克隆仓库

git clone https://github.com/lllssssyyy/lsy-repository.git
cd classhelper

# 安装依赖

pip install -r requirements.txt

# 初始化数据库

python -c "from app import app, db; with app.app_context(): db.create_all()"

# 启动应用

python app.py
# 访问 http://127.0.0.1:5000
默认教师账号：teacher / 123456 (需手动注册，或添加初始化脚本)
