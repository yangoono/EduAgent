from operator import or_
from flask import render_template, flash, redirect, url_for, request, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
import numpy as np
import requests
import json
import io
import csv
import pandas as pd
from app import app, db
from app.models import User, Student, Score, Course
from app.forms import LoginForm, RegisterForm

# client = OpenAI(
#       api_key=os.environ.get("AI_STUDIO_API_KEY"),  # 含有 AI Studio 访问令牌的环境变量，https://aistudio.baidu.com/account/accessToken  ,
#       base_url="https://qianfan.baidubce.com/v2/chat/completions  ",  # aistudio 大模型 api 服务域名
# )

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = '请登录后访问数据仪表盘页面'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(id):
    '''
    用户加载回调函数。
    Flask-Login使用此函数根据用户ID从数据库中加载用户对象。
    '''
    return User.query.get(id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    登录路由。
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = None
        if form.email.data:
            user = User.query.filter_by(email=form.email.data).first()
        elif form.phone.data:
            user = User.query.filter_by(phone=form.phone.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码无效', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        flash('登录成功!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    注册路由。
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        email_exists = User.query.filter_by(email=form.email.data).first()
        phone_exists = User.query.filter_by(phone=form.phone.data).first()
        
        if phone_exists:
            flash('手机号已被注册。请使用其他邮箱或登录', 'danger')
            return render_template('auth/register.html', form=form)
        
        if email_exists:
            flash('邮箱已被注册。请使用其他邮箱或登录。', 'danger')
            return render_template('auth/register.html', form=form)
        user = User(email=form.email.data, phone=form.phone.data, name=form.name.data) # type: ignore
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功!', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """
    登出路由。
    清除当前用户的会话信息并重定向到登录页面。
    """
    logout_user()
    return redirect(url_for('login'))

# --- 页面路由 ---
@app.route('/')
@login_required
def dashboard():
    """
    主仪表盘页面路由。
    需要用户登录后才能访问。
    """
    return render_template('auth/dashboard.html')

# ------------------
# 学生管理API
# -----------------
@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    """
    获取所有学生列表。
    响应格式:
    [
        {"sno": "学号", "sname": "姓名", ...},
        ...
    ]
    """
    students = Student.query.all()
    return jsonify([s.to_dict() for s in students])

@app.route('/api/students', methods=['POST'])
@login_required
def add_student():
    """
    添加一个新学生。
    请求体 (JSON):
    {"sno": "学号", "sname": "姓名", "sage": 年龄, "ssex": "性别", "sdept": "专业", "hometown": "籍贯"}
    响应格式 (成功):
    {"success": true, "student": {"sno": "学号", ...}}
    """
    data = request.get_json()
    
    if not data or not all(key in data for key in ['sno', 'sname', 'sage', 'ssex', 'sdept', 'hometown']):
        return jsonify({'success': False, 'message': '缺少必要字段'}), 400
    
    try:
        new_student = Student(**data)
        db.session.add(new_student)
        db.session.commit()
        return jsonify({
            'success': True,
            'student': new_student.to_dict()
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '学号已存在'
        }), 400

@app.route('/api/students/<sno>', methods=['PUT'])
@login_required
def update_student(sno):
    """
    根据学号更新一个已存在的学生信息。
    路径参数:
        sno: 学生学号
    请求体 (JSON):
    {"sname": "新姓名", "sage": 新年龄, ...}
    响应格式 (成功):
    {"success": true, "student": {"sno": "学号", ...}}
    """
    data = request.get_json()
    student = Student.query.get_or_404(sno)
    
    # 更新字段
    student.sname = data.get('sname', student.sname)
    student.sage = data.get('sage', student.sage)
    student.ssex = data.get('ssex', student.ssex)
    student.sdept = data.get('sdept', student.sdept)
    student.hometown = data.get('hometown', student.hometown)
    
    db.session.commit()
    return jsonify({
        'success': True,
        'student': student.to_dict()
    })

@app.route('/api/students/<sno>', methods=['DELETE'])
@login_required
def delete_student(sno):
    """
    根据学号删除一个学生。
    路径参数:
        sno: 学生学号
    响应格式 (成功):
    {"success": true, "message": "学生删除成功"}
    """
    student = Student.query.get_or_404(sno)
    
    try:
        # 先删除该学生的所有成绩记录
        Score.query.filter_by(sno=sno).delete()
        # 然后删除学生记录
        db.session.delete(student)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '学生删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除学生失败: {str(e)}'
        }), 500

# ------------------
# 课程管理API
# -----------------
@app.route('/api/courses', methods=['GET'])
@login_required
def get_all_courses():
    """
    获取所有课程列表，支持通过查询参数进行筛选。
    查询参数:
        search: 课程号或课程名关键字
        teacher: 教师名关键字
        credit: 学分
    响应格式:
    [
        {"cno": "课程号", "cname": "课程名", ...},
        ...
    ]
    """
    search_query = request.args.get('search', None)
    teacher_query = request.args.get('teacher', None)
    credit_query = request.args.get('credit', None)

    query = Course.query

    # 使用 or_ 和 ilike 实现模糊查询
    if search_query:
        query = query.filter(or_(
            Course.cno.ilike(f"%{search_query}%"),
            Course.cname.ilike(f"%{search_query}%")
        ))

    if teacher_query:
        query = query.filter(Course.cteacher.ilike(f"%{teacher_query}%"))
    if credit_query:
        try:
            credit_value = int(credit_query)
            query = query.filter(Course.ccredit == credit_value)
        except ValueError:
            pass

    courses = query.all()
    return jsonify([c.to_dict() for c in courses])

@app.route('/api/courses/<cno>', methods=['GET'])
@login_required
def get_course(cno):
    """
    根据课程号查询单个课程信息。
    路径参数:
        cno: 课程号
    响应格式:
    {"cno": "课程号", "cname": "课程名", ...}
    """
    course = Course.query.get_or_404(cno)
    return jsonify(course.to_dict())

@app.route('/api/courses', methods=['POST'])
@login_required
def add_course():
    """
    添加一个新课程。
    请求体 (JSON):
    {"cno": "课程号", "cname": "课程名", "ccredit": 学分, "cteacher": "教师", "cpno": "先修课程号"}
    响应格式 (成功):
    {"success": true, "course": {"cno": "课程号", ...}}
    """
    data = request.get_json()
    
    # 必填字段验证
    required_fields = ['cno', 'cname', 'ccredit', 'cteacher']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': '缺少必要字段'}), 400
    
    try:
        new_course = Course(**data)
        db.session.add(new_course)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'course': new_course.to_dict()
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '课程号已存在'
        }), 400

@app.route('/api/courses/<cno>', methods=['PUT'])
@login_required
def update_course(cno):
    """
    根据课程号更新一个已存在的课程信息。
    路径参数:
        cno: 课程号
    请求体 (JSON):
    {"cname": "新课程名", "ccredit": 新学分, ...}
    响应格式 (成功):
    {"success": true, "course": {"cno": "课程号", ...}}
    """
    data = request.get_json()
    course = Course.query.get_or_404(cno)
    
    course.cname = data.get('cname', course.cname)
    course.cpno = data.get('cpno', course.cpno)
    course.ccredit = data.get('ccredit', course.ccredit)
    course.cteacher = data.get('cteacher', course.cteacher)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'course': course.to_dict()
    })

@app.route('/api/courses/<cno>', methods=['DELETE'])
@login_required
def delete_course(cno):
    """
    根据课程号删除一个课程。
    路径参数:
        cno: 课程号
    响应格式 (成功):
    {"success": true, "message": "课程删除成功"}
    """
    course = Course.query.get_or_404(cno)
    
    try:
        # 先删除该课程的所有成绩记录
        Score.query.filter_by(cno=cno).delete()
        # 然后删除课程记录
        db.session.delete(course)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '课程删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除课程失败: {str(e)}'
        }), 500



@app.route('/api/scores', methods=['GET'])
@login_required
def get_scores():
    """
    查询所有学生成绩，并将成绩与学生姓名和课程名称关联后返回。
    响应格式:
    [
        {"sno": "学号", "sname": "姓名", "cno": "课程号", "cname": "课程名", "score": 成绩},
        ...
    ]
    """
    # 从请求的查询参数中获取筛选条件
    student_query = request.args.get('student', None)  
    course_query = request.args.get('course', None)   
    score_query = request.args.get('score', None)   

    # 构造基础查询，联合查询 Score、Student 和 Course 表
    query = db.session.query(
        Score,
        Student.sname,  
        Course.cname   
    ).join(
        Student, Score.sno == Student.sno  
    ).join(
        Course, Score.cno == Course.cno   
    )

    # 如果有学生筛选条件
    if student_query:
        query = query.filter(or_(
            Student.sno.ilike(f"%{student_query}%"),  
            Student.sname.ilike(f"%{student_query}%") 
        ))

    # 如果有课程筛选条件
    if course_query:
        query = query.filter(or_(
            Course.cno.ilike(f"%{course_query}%"),  
            Course.cname.ilike(f"%{course_query}%") 
        ))

    # 如果有成绩筛选条件
    if score_query:
        try:
            min_score, max_score = map(float, score_query.split('-'))
            query = query.filter(Score.score >= min_score, Score.score <= max_score)
        except ValueError:
            return jsonify({'success': False, 'message': '成绩范围格式不正确，应为 "min-max"'}), 400

    scores = query.all()

    result = [{
        'sno': s.Score.sno,
        'sname': s.sname,
        'cno': s.Score.cno,
        'cname': s.cname,
        'score': s.Score.score
    } for s in scores]

    return jsonify(result)

@app.route('/api/scores', methods=['POST'])
@login_required
def add_score():
    """
    接收客户端发送的成绩数据，如果成绩已存在则更新，否则添加新成绩。
    请求体 (JSON):
    {"sno": "学号", "cno": "课程号", "score": 成绩}
    响应格式 (成功):
    {"success": true, "message": "...", "score": {...}}
    """
    data = request.get_json()
    
    required_fields = ['sno', 'cno', 'score']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': '缺少必要字段'}), 400
    
    try:
        # 检查成绩是否已存在
        existing_score = Score.query.filter_by(
            sno=data['sno'],
            cno=data['cno']
        ).first()
        
        if existing_score:
            # 更新已有成绩
            existing_score.score = data['score']
            db.session.commit()
            return jsonify({
                'success': True,
                'message': '成绩更新成功',
                'score': existing_score.to_dict()
            })
        else:
            # 创建新成绩记录
            new_score = Score(**data)
            db.session.add(new_score)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': '成绩添加成功',
                'score': new_score.to_dict()
            })
            
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '操作失败: 学生或课程不存在'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }), 500

@app.route('/api/scores/<sno>/<cno>', methods=['PUT'])
@login_required
def update_score(sno, cno):
    """
    修改某个学生某门课的成绩
    请求体: { "score": 新成绩 }
    """
    data = request.get_json()
    if not data or 'score' not in data:
        return jsonify({'success': False, 'message': '缺少成绩字段'}), 400

    score_obj = Score.query.filter_by(sno=sno, cno=cno).first()
    if not score_obj:
        return jsonify({'success': False, 'message': '成绩记录不存在'}), 404

    try:
        score_obj.score = data['score']
        db.session.commit()
        return jsonify({'success': True, 'message': '成绩修改成功', 'score': score_obj.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500

@app.route('/api/scores/<sno>/<cno>', methods=['DELETE'])
@login_required
def delete_score(sno, cno):
    """
    删除某个学生某门课的成绩
    """
    score_obj = Score.query.filter_by(sno=sno, cno=cno).first()
    if not score_obj:
        return jsonify({'success': False, 'message': '成绩记录不存在'}), 404

    try:
        db.session.delete(score_obj)
        db.session.commit()
        return jsonify({'success': True, 'message': '成绩删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500

#--------------------
# 数据分析API
#--------------------
@app.route('/api/analysis/avg_score_by_dept', methods=['GET'])
@login_required
def avg_score_by_dept():
    """
    计算并返回各专业的平均成绩。
    响应格式:
    {
        "depts": ["专业1", "专业2", ...],
        "scores": [平均分1, 平均分2, ...]
    }
    """
    result = db.session.query(
        Student.sdept,
        db.func.avg(Score.score).label('avg_score')
    ).join(
        Score, Student.sno == Score.sno
    ).group_by(
        Student.sdept
    ).all()
    
    return jsonify({
        'depts': [r.sdept for r in result],
        'scores': [float(r.avg_score) for r in result]
    })

@app.route('/api/analysis/student_origin', methods=['GET'])
@login_required
def student_origin():
    """
    统计并返回学生生源地分布数据。
    响应格式:
    {
        "hometowns": ["生源地1", "生源地2", ...],
        "counts": [人数1, 人数2, ...]
    }
    """
    result = db.session.query(
        Student.hometown,
        db.func.count(Student.sno).label('count')
    ).group_by(
        Student.hometown
    ).all()
    
    return jsonify({
        'hometowns': [r.hometown for r in result],
        'counts': [r.count for r in result]
    })

@app.route('/api/analysis/student_radar/<sno>', methods=['GET'])
@login_required
def student_radar(sno):
    """
    返回指定学生的各科成绩数据，用于雷达图。
    路径参数:
        sno: 学生学号
    响应格式:
    {
        "courses": ["课程1", "课程2", ...],
        "scores": [成绩1, 成绩2, ...]
    }
    """
    scores = db.session.query(
        Course.cname,
        Score.score
    ).join(
        Score, Course.cno == Score.cno
    ).filter(
        Score.sno == sno
    ).all()
    
    if not scores:
        return jsonify({
            'courses': [],
            'scores': []
        })
    
    return jsonify({
        'courses': [s.cname for s in scores],
        'scores': [s.score for s in scores]
    })

@app.route('/api/analysis/course_distribution/<cno>', methods=['GET'])
@login_required
def course_distribution(cno):
    """
    返回指定课程的成绩分布数据，用于饼图和箱线图。
    路径参数:
        cno: 课程号
    响应格式:
    {
        "course_name": "课程名称",
        "pie_data": [{"value": 数量, "name": "分数段"}, ...],
        "boxplot_data": {"boxData": [所有成绩列表]}
    }
    """
    # 获取课程名称
    course = Course.query.get_or_404(cno)
    
    # 获取所有成绩
    scores = [s.score for s in Score.query.filter_by(cno=cno).all() if s.score is not None]
    
    if not scores:
        return jsonify({
            'course_name': course.cname,
            'pie_data': [],
            'boxplot_data': {'boxData': []}
        })
    
    # 生成饼图数据(按分数段分组)
    bins = [0, 60, 70, 80, 90, 101] # 上限设为101以包含100分
    labels = ['不及格 (0-59)', '及格 (60-69)', '中等 (70-79)', '良好 (80-89)', '优秀 (90-100)']
    hist, _ = np.histogram(scores, bins=bins)
    
    pie_data = [{
        'value': int(count),
        'name': label
    } for count, label in zip(hist, labels) if count > 0] # 只显示有学生的分布
    
    return jsonify({
        'course_name': course.cname,
        'pie_data': pie_data,
        'boxplot_data': {
            'boxData': scores
        }
    })

#--------------------
# AI分析及CSV导入导出API
#--------------------

def get_llm_analysis(data_type, identifier):
    """
    调用文心大模型进行数据分析
    参数:
        data_type: 'student' 或 'course'
        identifier: 学号(sno)或课程号(cno)
    返回:
        str: 大模型生成的分析结果
    """
    prompt = None
    url = "https://qianfan.baidubce.com/v2/chat/completions"
    try:
        if data_type == 'student':
            # 获取学生数据
            student = Student.query.get(identifier)
            if not student:
                return "找不到该学生信息"
            
            # 获取学生成绩
            scores = db.session.query(
                Course.cname,
                Score.score
            ).join(
                Score, Course.cno == Score.cno
            ).filter(
                Score.sno == identifier
            ).all()
            
            # 构造提示词
            system_prompt = "你是一个经验丰富、温柔的教育专家，擅长根据学生的成绩和学习情况提供个性化的学习建议。"
            prompt = f"""
            请分析以下学生数据并提供学习建议：
            
            学生信息：
            - 学号: {student.sno}
            - 姓名: {student.sname}
            - 专业: {student.sdept}
            - 年龄: {student.sage}
            
            成绩信息：
            {chr(10).join(f"- {s.cname}: {s.score}" for s in scores)}
            
            请用中文回答，分析应包括：
            1. 整体学习情况评价
            2. 优势科目和待改进科目
            3. 具体学习建议
            4. 针对专业的建议
            格式要求：不要使用Markdown格式
            """
        elif data_type == 'course':
            # 获取课程数据
            course = Course.query.get(identifier)
            if not course:
                return "找不到该课程信息"
            
            # 获取课程成绩统计
            scores = [s.score for s in Score.query.filter_by(cno=identifier).all()]
            avg_score = sum(scores)/len(scores) if scores else 0
            
            system_prompt = "你是一个经验丰富的教育专家，擅长根据课程的教学效果和成绩分布提供个性化的教学建议。"
            prompt = f"""
            请分析以下课程数据并提供教学建议：
            
            课程信息：
            - 课程号: {course.cno}
            - 课程名: {course.cname}
            - 学分: {course.ccredit}
            - 教师: {course.cteacher}
            
            成绩统计：
            - 平均分: {avg_score:.1f}
            - 最高分: {max(scores) if scores else 0}
            - 最低分: {min(scores) if scores else 0}
            - 及格率: {sum(1 for s in scores if s >= 60)/len(scores)*100 if scores else 0:.1f}%
            
            请用中文回答，分析应包括：
            1. 课程整体教学效果评价
            2. 成绩分布特点分析
            3. 教学改进建议
            4. 对学生学习的建议
            格式要求：不要使用markdown
            """
            
    except Exception as e:
        return f"分析过程中出错: {str(e)}"
    
    if prompt:
        payload = json.dumps({
        "model": "ernie-3.5-8k",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer bce-v3/ALTAK-Ql9AdJAHL15RJXd0eFGRT/4b961c1c585a90c7227a7a0848a1b4dc263f1035'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        
        # print(response.text)
        res = json.loads(response.text)
        return res['choices'][0]['message']['content']
    
    return "无法进行分析，数据类型不支持。"

@app.route('/api/ai_analysis/student/<sno>', methods=['GET'])
def ai_analyze_student(sno):
    """
    调用文心大模型进行学生分析
    参数:
        sno: 学生学号
    返回:
        str: 大模型生成的分析结果
    """
    try:
        analysis_text = get_llm_analysis('student', sno)
        return jsonify({"success": True, "analysis": analysis_text})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/ai_analysis/course/<cno>', methods=['GET'])
def ai_analyze_course(cno):
    """
    调用文心大模型进行课程分析
    参数:
        cno: 课程号
    返回:
        str: 大模型生成的分析结果
    """
    try:
        analysis_text = get_llm_analysis('course', cno)
        return jsonify({"success": True, "analysis": analysis_text})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def get_filtered_students_from_db(sno_sname=None, sdept=None, sgrade=None, sclass=None):
    """
    根据多种筛选条件从数据库获取学生数据的内部辅助函数。
    参数:
        sno_sname: 学号或姓名 (模糊匹配)
        sdept: 专业 (精确匹配)
        sgrade: 年级 (前缀匹配)
        sclass: 班级 (前缀匹配)
    返回:
        筛选后的Student对象列表
    """
    query = Student.query

    if sno_sname:
        query = query.filter((Student.sno.ilike(f'%{sno_sname}%')) | (Student.sname.ilike(f'%{sno_sname}%')))
    if sdept:
        query = query.filter_by(sdept=sdept)
    if sgrade:
        sgrade_prefix = sgrade[2:]
        query = query.filter(Student.sno.startswith(sgrade_prefix))
    if sclass:
        query = query.filter(Student.sno.startswith(sclass))

    return query.all()

@app.route('/api/students/export-csv')
@login_required
def export_student_csv():
    """
    根据查询参数筛选学生数据，并将其导出为CSV文件。
    查询参数:
        searchText, sdept, sgrade, sclass
    """
    try:
        search_text = request.args.get('searchText')
        sdept = request.args.get('sdept')
        sgrade = request.args.get('sgrade')
        sclass = request.args.get('sclass')

        students = get_filtered_students_from_db(sno_sname=search_text, sdept=sdept, sgrade=sgrade, sclass=sclass)

        if not students:
            return jsonify({'success': False, 'message': '没有找到匹配的学生数据，无法导出。'}), 404

        si = io.StringIO()
        cw = csv.writer(si)
        headers = ['学号', '姓名', '性别', '年龄', '专业', '籍贯']
        cw.writerow(headers)

        for student in students:
            cw.writerow([student.sno, student.sname, student.ssex, student.sage, student.sdept, student.hometown])

        output = io.BytesIO(si.getvalue().encode('utf-8'))
        output.seek(0)

        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='students.csv')

    except Exception as e:
        print(f"导出学生CSV时发生错误: {e}")
        return jsonify({'success': False, 'message': f'导出学生数据失败: {str(e)}'}), 500

STUDENT_CSV_HEADERS_MAP = {
    '学号': 'sno', '姓名': 'sname', '性别': 'ssex',
    '年龄': 'sage', '专业': 'sdept', '籍贯': 'hometown',
}

COURSE_CSV_HEADERS_MAP = {
    '课程号': 'cno', '课程名': 'cname', '学分': 'ccredit', '教师': 'cteacher',
}
SCORE_CSV_HEADERS_MAP ={
    '学号': 'sno', '课程号': 'cno', '成绩': 'score',
}
def _process_uploaded_file(file):
    """Helper function to process uploaded file and return text stream."""
    if not file or not file.filename:
        return None
    
    raw_bytes = file.stream.read()
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = raw_bytes.decode('gbk')
    return io.StringIO(text)

def _validate_headers(csv_reader, required_headers_map):
    """Validate CSV headers against required headers map."""
    required_headers = list(required_headers_map.keys())
    if not csv_reader.fieldnames or not all(h in csv_reader.fieldnames for h in required_headers):
        missing = [h for h in required_headers if not csv_reader.fieldnames or h not in csv_reader.fieldnames]
        return False, missing
    return True, None

def _import_data(file, model, headers_map, process_row_func):
    """Generic import function for both students and courses."""
    stream = _process_uploaded_file(file)
    if not stream:
        return {'success': False, 'message': '文件无效或为空。'}, 400
    
    csv_reader = csv.DictReader(stream)
    is_valid, missing = _validate_headers(csv_reader, headers_map)
    if not is_valid:
        return {'success': False, 'message': f'CSV文件缺少列头: {", ".join(str(h) for h in missing)}'}, 400 #type: ignore

    new_count, updated_count, errors = 0, 0, []
    
    for row_num, row in enumerate(csv_reader, 2):
        try:
            result = process_row_func(row, headers_map, model)
            if result == 'new':
                new_count += 1
            elif result == 'updated':
                updated_count += 1
        except Exception as e:
            errors.append(f"第 {row_num} 行处理失败: {e}")
    
    db.session.commit()
    
    message = f"上传成功！新增 {new_count} 条，更新 {updated_count} 条。"
    if errors:
        message += f" 出现 {len(errors)} 条错误。"
        print("导入错误:", errors)

    return {'success': True, 'message': message}, 200

def _process_student_row(row, headers_map, model):
    student_data = {model_field: row.get(csv_header, '').strip() 
                   for csv_header, model_field in headers_map.items()}
    student_data['sage'] = int(student_data['sage']) if student_data['sage'].isdigit() else None
    
    sno = student_data.get('sno')
    if not sno:
        raise ValueError("学号为空")
    
    existing_student = model.query.get(sno)
    if existing_student:
        for key, value in student_data.items():
            setattr(existing_student, key, value)
        return 'updated'
    else:
        new_student = model(**student_data)
        db.session.add(new_student)
        return 'new'

def _process_course_row(row, headers_map, model):
    course_data = {model_field: row.get(csv_header, '').strip() 
                  for csv_header, model_field in headers_map.items()}
    
    cno = course_data.get('cno')
    if not cno:
        raise ValueError("课程号为空")
    
    existing_course = model.query.get(cno)
    if existing_course:
        for key, value in course_data.items():
            setattr(existing_course, key, value)
        return 'updated'
    else:
        new_course = model(**course_data)
        db.session.add(new_course)
        return 'new'
def  _process_score_row(row, headers_map, model):
    score_data = {model_field: row.get(csv_header, '').strip() 
                  for csv_header, model_field in headers_map.items()}
    
    sno = score_data.get('sno')
    cno = score_data.get('cno')
    score = score_data.get('score')

    existing_score = model.query.filter_by(sno=sno, cno=cno).first()
    if existing_score:
        for key, value in score_data.items():
            setattr(existing_score, key, value)
        return 'updated'
    else:
        new_score = model(**score_data) 
        db.session.add(new_score)
        return 'new'

def import_students_from_csv(file):
    return _import_data(file, Student, STUDENT_CSV_HEADERS_MAP, _process_student_row)

def import_courses_from_csv(file):
    return _import_data(file, Course, COURSE_CSV_HEADERS_MAP, _process_course_row)

def import_scores_from_csv(file):
    return _import_data(file, Score, SCORE_CSV_HEADERS_MAP, _process_score_row)


@app.route('/api/import-csv', methods=['POST'])
@login_required
def import_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到文件部分。'}), 400

    file = request.files['file']
    upload_type = request.form.get('type')

    if not file or not file.filename:
        return jsonify({'success': False, 'message': '文件无效或为空。'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': '仅支持CSV格式文件。'}), 400

    import_functions = {
        'students': import_students_from_csv,
        'courses': import_courses_from_csv,
        'scores': import_scores_from_csv,
    }

    if upload_type not in import_functions:
        return jsonify({'success': False, 'message': '不支持的上传类型。'}), 400

    result, status_code = import_functions[upload_type](file)
    return jsonify(result), status_code