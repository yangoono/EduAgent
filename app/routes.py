from operator import or_
from flask import render_template, flash, redirect, url_for, request, jsonify, send_file, current_app, g, Response, stream_with_context
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import jwt
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import numpy as np
import requests
import json
import io
import csv
import pandas as pd
from app import app, db
from app.models import User, Student, Score, Course, KnowledgeDoc, Teacher, Role, Permission
from app.forms import LoginForm, RegisterForm
from app.decorators import require_role, jwt_required
from app.ai.risk_predictor import calculate_risk
from app.rag.pipeline import query_rag, add_document, process_pdf
from app.agents.teacher_agent import get_teacher_response
from app.agents.student_agent import get_student_response
from app.agents.admin_agent import get_admin_response
from app.edge.minicpm_v import extract_structured_data_from_image

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
        elif form.sno.data:
            user = User.query.filter_by(sno=form.sno.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码无效', 'danger')
            return redirect(url_for('login'))
        
        # 签发 JWT
        token = jwt.encode({
            'user_id': user.id,
            'role': user.role,
            'sno': user.sno,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        # 同时保留 Session 登录兼容旧页面
        login_user(user, remember=form.remember_me.data)
        
        # 如果是AJAX请求，返回JSON，否则渲染模板
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': True, 'token': token, 'role': user.role})
            
        # 这里为了演示JWT存储，我们将Token通过JS种到LocalStorage
        # 实际开发中可以通过专门的/api/login分离
        flash('登录成功!', 'success')
        response = redirect(url_for('dashboard'))
        response.set_cookie('temp_token', token) # 用于页面跳转后提取存储
        return response
    else:
        if request.method == 'POST':
            print(f"Login form validation failed: {form.errors}")
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
        user = User(email=form.email.data, phone=form.phone.data, name=form.name.data, sno=form.sno.data, role=form.role.data) # type: ignore
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin')
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
@jwt_required
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
@jwt_required
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin')
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
@jwt_required
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

    # 如果是学生角色，强制覆盖学生查询条件为其自己的学号
    if g.current_user_role == 'student':
        student_query = g.current_sno


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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
@require_role('admin', 'teacher')
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
@jwt_required
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
@jwt_required
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
@jwt_required
def student_radar(sno):
    # 保留原接口兼容性，但不再推荐使用，新前端将使用 student_dashboard 接口
    scores = db.session.query(Course.cname, Score.score).join(Score, Course.cno == Score.cno).filter(Score.sno == sno).all()
    if not scores: return jsonify({'courses': [], 'scores': []})
    return jsonify({'courses': [s.cname for s in scores], 'scores': [s.score for s in scores]})

@app.route('/api/analysis/student_dashboard/<sno>', methods=['GET'])
@jwt_required
def student_dashboard(sno):
    """
    学生综合仪表盘接口：返回雷达图数据、专业排名、及学业预警状态。
    基于《桂电教〔2025〕28号》规则：
    黄：挂科>=3门或学分>=10；橙：挂科>=4门或学分>=15；红：挂科>=5门或学分>=20；退学：累计挂科学分>=25
    """
    student = Student.query.get(sno)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # 1. 雷达图成绩数据
    course_scores = db.session.query(Course.cname, Course.ccredit, Score.score).join(
        Score, Course.cno == Score.cno).filter(Score.sno == sno).all()
    
    radar_courses = [cs.cname for cs in course_scores]
    radar_scores = [cs.score for cs in course_scores]
    radar_credits = [cs.ccredit for cs in course_scores]
    
    # 2. 学业预警判定 (Academic Warning)
    failed_count = 0
    failed_credits = 0
    for cs in course_scores:
        if cs.score < 60:
            failed_count += 1
            failed_credits += cs.ccredit
            
    warning_status = 'safe'
    warning_level = 0
    
    if failed_credits >= 25:
        warning_status = 'expulsion'
        warning_level = 4
    elif failed_count >= 5 or failed_credits >= 20:
        warning_status = 'red'
        warning_level = 3
    elif failed_count >= 4 or failed_credits >= 15:
        warning_status = 'orange'
        warning_level = 2
    elif failed_count >= 3 or failed_credits >= 10:
        warning_status = 'yellow'
        warning_level = 1
        
    warning_info = {
        'status': warning_status,
        'level': warning_level,
        'failed_count': failed_count,
        'failed_credits': failed_credits
    }

    # 3. 排名与超越百分比
    # 计算全专业的学生平均分
    dept_students = Student.query.filter_by(sdept=student.sdept).all()
    dept_snos = [s.sno for s in dept_students]
    
    # 获取专业所有学生的成绩聚合
    all_scores = db.session.query(Score.sno, db.func.avg(Score.score).label('avg')).filter(
        Score.sno.in_(dept_snos)).group_by(Score.sno).all()
        
    # 排序计算排名
    all_scores.sort(key=lambda x: x.avg or 0, reverse=True)
    total_students = len(all_scores)
    
    my_rank = total_students
    my_avg = 0
    for i, s_record in enumerate(all_scores):
        if s_record.sno == sno:
            my_rank = i + 1
            my_avg = float(s_record.avg or 0)
            break
            
    beat_percentage = 0
    if total_students > 1:
        beat_percentage = round(((total_students - my_rank) / total_students) * 100, 1)

    rank_info = {
        'rank': my_rank,
        'total': total_students,
        'beat_percentage': beat_percentage,
        'avg_score': round(my_avg, 2),
        'dept': student.sdept
    }

    return jsonify({
        'radar': {'courses': radar_courses, 'scores': radar_scores, 'credits': radar_credits},
        'warning': warning_info,
        'rank': rank_info
    })

@app.route('/api/analysis/course_distribution/<cno>', methods=['GET'])
@jwt_required
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
        'boxplot_data': {'boxData': scores}
    })

@app.route('/api/analysis/course_correlation', methods=['GET'])
@jwt_required
def course_correlation():
    """
    使用 Apriori 思想进行课程及格率关联分析。
    """
    from collections import defaultdict
    
    # 提取所有及格(>=60)的成绩记录
    passing_scores = db.session.query(Score.sno, Score.cno).filter(Score.score >= 60).all()
    
    # 获取课程字典映射
    courses = {c.cno: c.cname for c in Course.query.all()}
    
    # 按学生分组
    student_courses = defaultdict(set)
    for sno, cno in passing_scores:
        student_courses[sno].add(cno)
        
    total_students = len(student_courses)
    if total_students == 0:
        return jsonify({'nodes': [], 'links': []})
        
    # 计算 support
    course_support = defaultdict(int)
    pair_support = defaultdict(int)
    
    for sno, cnos in student_courses.items():
        cno_list = list(cnos)
        for c in cno_list:
            course_support[c] += 1
            
        for i in range(len(cno_list)):
            for j in range(i + 1, len(cno_list)):
                c1, c2 = cno_list[i], cno_list[j]
                if c1 > c2:
                    c1, c2 = c2, c1
                pair_support[(c1, c2)] += 1
                
    nodes = []
    links = []
    
    # 添加节点
    for cno, count in course_support.items():
        nodes.append({
            'id': cno,
            'name': courses.get(cno, cno),
            'value': count, # 频次越高，节点越大
            'symbolSize': min(count * 2, 60) # 视觉缩放
        })
        
    # 添加边 (置信度过滤)
    for (c1, c2), count in pair_support.items():
        support = count / total_students
        # 简单过滤关联不够强的
        if count >= 3: 
            links.append({
                'source': c1,
                'target': c2,
                'value': count,
                'label': {'show': False}
            })
            
    return jsonify({
        'nodes': nodes,
        'links': links
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
            'Authorization': ''
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

@app.route('/api/ai/risk/<sno>', methods=['GET'])
@jwt_required
def get_student_risk(sno):
    """
    获取学生的学业风险预测
    """
    student = Student.query.get_or_404(sno)
    scores = db.session.query(
        Course.cname,
        Course.ccredit,
        Score.score
    ).join(
        Score, Course.cno == Score.cno
    ).filter(
        Score.sno == sno
    ).all()
    
    scores_data = [{'cname': s.cname, 'score': s.score, 'ccredit': s.ccredit} for s in scores]
    risk_level, explanation = calculate_risk(scores_data)
    
    return jsonify({
        'success': True,
        'sno': sno,
        'risk_level': risk_level,
        'reason': explanation
    })

# -----------------
# RAG 校园知识库 API
# -----------------
@app.route('/api/rag/query', methods=['POST'])
@jwt_required
def api_rag_query():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({'success': False, 'message': '请输入问题'}), 400
        
    answer, sources = query_rag(question)
    return jsonify({
        'success': True,
        'answer': answer,
        'sources': sources
    })

@app.route('/api/rag/docs', methods=['GET'])
@jwt_required
@require_role('admin')
def api_rag_docs():
    docs = KnowledgeDoc.query.all()
    # 避免返回庞大的 embedding 数据
    return jsonify([
        {
            'id': d.id,
            'title': d.title,
            'content': d.content
        } for d in docs
    ])

@app.route('/api/rag/upload', methods=['POST'])
@jwt_required
@require_role('admin')
def api_rag_upload():
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    if not title or not content:
        return jsonify({'success': False, 'message': '缺少标题或内容'}), 400
        
    try:
        docs = add_document(title, content)
        return jsonify({'success': True, 'docs': [d.to_dict() for d in docs]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/rag/upload_pdf', methods=['POST'])
@jwt_required
@require_role('admin')
def api_rag_upload_pdf():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到文件部分'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        import tempfile
        import os
        try:
            # 存为临时文件供 process_pdf 处理
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            file.save(temp_path)
            
            title_prefix = file.filename.replace('.pdf', '')
            docs_added = process_pdf(temp_path, title_prefix=title_prefix)
            
            os.remove(temp_path)
            
            if not docs_added:
                return jsonify({'success': False, 'message': 'PDF解析失败或内容为空'}), 400
                
            return jsonify({'success': True, 'message': f'成功解析 PDF 并添加 {len(docs_added)} 个分块到知识库'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        return jsonify({'success': False, 'message': '仅支持 PDF 文件'}), 400

# -----------------
# 多 Agent 系统 API
# -----------------
@app.route('/api/agent/teacher', methods=['POST'])
@jwt_required
def api_agent_teacher():
    data = request.get_json()
    message = data.get('message')
    history = data.get('history', [])
    if not message:
        return jsonify({'success': False, 'message': '消息为空'}), 400
    
    reply, thinking_steps, echarts_option = get_teacher_response(message, history)
    return jsonify({'success': True, 'reply': reply, 'thinking_steps': thinking_steps, 'echarts_option': echarts_option})

@app.route('/api/agent/student', methods=['POST'])
@jwt_required
def api_agent_student():
    data = request.get_json()
    message = data.get('message')
    history = data.get('history', [])
    if not message:
        return jsonify({'success': False, 'message': '消息为空'}), 400
    
    current_sno = getattr(current_user, 'sno', None)
    
    reply, history, thinking_steps, echarts_option = get_student_response(message, history, current_sno=current_sno)
    return jsonify({'success': True, 'reply': reply, 'thinking_steps': thinking_steps, 'echarts_option': echarts_option})

@app.route('/api/agent/admin', methods=['POST'])
@jwt_required
@require_role('admin')
def api_agent_admin():
    data = request.get_json()
    message = data.get('message')
    history = data.get('history', [])
    if not message:
        return jsonify({'success': False, 'message': '消息为空'}), 400
    
    reply, thinking_steps, echarts_option = get_admin_response(message, history)
    return jsonify({'success': True, 'reply': reply, 'thinking_steps': thinking_steps, 'echarts_option': echarts_option})

# -----------------
# SSE 流式输出接口 (Server-Sent Events)
# -----------------
@app.route('/api/agent/stream', methods=['POST'])
@jwt_required
def api_agent_stream():
    """
    SSE 流式端点：实时推送 Coordinator 的每一步思考过程。
    前端监听此接口可实现“AI 思考中”的实时动画效果。
    """
    import queue
    import threading
    from app.agents.coordinator import run_coordinator

    data = request.get_json()
    message = data.get('message', '')
    if not message:
        return jsonify({'success': False, 'message': '消息为空'}), 400

    current_role = getattr(current_user, 'role', 'student')
    current_sno = getattr(current_user, 'sno', None)

    q = queue.Queue()

    def on_step(msg):
        q.put({'type': 'step', 'content': msg})

    def run_agent():
        try:
            result = run_coordinator(message, current_role=current_role, current_sno=current_sno, step_callback=on_step)
            q.put({'type': 'done', 'answer': result.get('answer', ''), 'echarts_option': result.get('echarts_option')})
        except Exception as e:
            q.put({'type': 'error', 'content': str(e)})

    threading.Thread(target=run_agent, daemon=True).start()

    def generate():
        while True:
            item = q.get()
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item['type'] in ('done', 'error'):
                break

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

# -----------------
@app.route('/api/edge/ocr', methods=['POST'])
def api_edge_ocr():
    """
    接收前端传来的图片，调用端侧模型提取结构化数据。
    这里不保存原始图片，只返回 JSON，贯彻隐私保护思想。
    """
    image_bytes = None
    data_type = 'score'
    
    if request.is_json:
        req_data = request.get_json()
        if 'image_base64' in req_data:
            import base64
            try:
                image_bytes = base64.b64decode(req_data['image_base64'])
            except Exception as e:
                return jsonify({'success': False, 'message': f'Base64解码失败: {e}'}), 400
        data_type = req_data.get('data_type', 'score')
    
    if not image_bytes:
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                image_bytes = file.read()
        data_type = request.form.get('data_type', 'score')

    if not image_bytes:
        return jsonify({'success': False, 'message': '未找到图片数据，请提供 multipart/form-data ("image") 或 JSON ("image_base64")'}), 400
        
    extracted_data = extract_structured_data_from_image(image_bytes, data_type)
    
    return jsonify({'success': True, 'data': extracted_data})

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
@jwt_required
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
@jwt_required
def import_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到文件部分。'}), 400

    file = request.files['file']
    upload_type = request.form.get('type')

    if not file or not file.filename:
        return jsonify({'success': False, 'message': '文件无效或为空。'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': '仅支持CSV格式文件。'}), 400

# ------------------
# 教师管理API
# -----------------
@app.route('/api/teachers', methods=['GET'])
@jwt_required
def get_teachers():
    teachers = Teacher.query.all()
    return jsonify([t.to_dict() for t in teachers])

@app.route('/api/teachers', methods=['POST'])
@jwt_required
@require_role('admin')
def add_teacher():
    data = request.get_json()
    if not data or not all(key in data for key in ['tno', 'tname', 'tdept', 'title']):
        return jsonify({'success': False, 'message': '缺少必要字段'}), 400
    try:
        new_teacher = Teacher(**data)
        db.session.add(new_teacher)
        db.session.commit()
        return jsonify({'success': True, 'teacher': new_teacher.to_dict()}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': '工号已存在'}), 400

@app.route('/api/teachers/<tno>', methods=['PUT'])
@jwt_required
@require_role('admin')
def update_teacher(tno):
    data = request.get_json()
    teacher = Teacher.query.get_or_404(tno)
    teacher.tname = data.get('tname', teacher.tname)
    teacher.tsex = data.get('tsex', teacher.tsex)
    teacher.tdept = data.get('tdept', teacher.tdept)
    teacher.title = data.get('title', teacher.title)
    db.session.commit()
    return jsonify({'success': True, 'teacher': teacher.to_dict()})

@app.route('/api/teachers/<tno>', methods=['DELETE'])
@jwt_required
@require_role('admin')
def delete_teacher(tno):
    teacher = Teacher.query.get_or_404(tno)
    db.session.delete(teacher)
    db.session.commit()
    return jsonify({'success': True, 'message': '教师已删除'})

# ------------------
# RBAC: 角色与权限管理API
# -----------------
@app.route('/api/roles', methods=['GET'])
@jwt_required
def get_roles():
    roles = Role.query.all()
    return jsonify([r.to_dict() for r in roles])

@app.route('/api/roles', methods=['POST'])
@jwt_required
@require_role('admin')
def add_role():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'message': '缺少必要字段'}), 400
    try:
        new_role = Role(name=data['name'], description=data.get('description', ''))
        db.session.add(new_role)
        db.session.commit()
        return jsonify({'success': True, 'role': new_role.to_dict()}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': '角色已存在'}), 400

@app.route('/api/permissions', methods=['GET'])
@jwt_required
def get_permissions():
    permissions = Permission.query.all()
    return jsonify([p.to_dict() for p in permissions])

@app.route('/api/users/<int:user_id>/roles', methods=['POST'])
@jwt_required
@require_role('admin')
def assign_role(user_id):
    data = request.get_json()
    user = User.query.get_or_404(user_id)
    if 'role' in data:
        user.role = data['role']
        db.session.commit()
        return jsonify({'success': True, 'message': '角色分配成功'})
    return jsonify({'success': False, 'message': '缺少 role 字段'}), 400
