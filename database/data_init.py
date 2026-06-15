import random
import csv
import os
from faker import Faker

from app import app, db
from app.models import Student, Course, Score

fake = Faker('zh_CN')

def generate_data():
    """生成模拟数据并插入数据库，然后导出到CSV文件"""

    # 清空现有数据
    db.drop_all()
    db.create_all()

    majors = ['数据科学与大数据技术', '机器人工程', '人工智能']
    genders = ['男', '女']
    
    # 1. 课程数据构建 (基于桂电人工智能学院培养方案)
    course_list = [
        # 公共基础课
        {'cno': 'C001', 'cname': '高等数学上', 'ccredit': 5, 'cteacher': fake.name(), 'cpno': None},
        {'cno': 'C002', 'cname': '高等数学下', 'ccredit': 5, 'cteacher': fake.name(), 'cpno': 'C001'},
        {'cno': 'C003', 'cname': '线性代数', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C001'},
        {'cno': 'C004', 'cname': '概率论与数理统计', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C002'},
        {'cno': 'C005', 'cname': '大学物理', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C001'},
        {'cno': 'C006', 'cname': '大学英语', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': None},
        # 专业基础与核心课
        {'cno': 'C007', 'cname': 'C语言程序设计', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': None},
        {'cno': 'C008', 'cname': '算法及数据结构', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C007'},
        {'cno': 'C009', 'cname': '计算机组成原理', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': None},
        {'cno': 'C010', 'cname': '计算机网络', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': None},
        {'cno': 'C011', 'cname': '数据库原理与应用', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C008'},
        {'cno': 'C012', 'cname': '人工智能基础', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C007'},
        {'cno': 'C013', 'cname': '机器学习与模式识别', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C012'},
        # 数据科学与大数据技术
        {'cno': 'C014', 'cname': '大数据可视化', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C011'},
        {'cno': 'C015', 'cname': '大数据原理与云计算', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C010'},
        {'cno': 'C016', 'cname': '数据挖掘（双语）', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C013'},
        # 人工智能专业
        {'cno': 'C017', 'cname': '数字图像处理', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C008'},
        {'cno': 'C018', 'cname': '深度学习与计算机视觉', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C013'},
        {'cno': 'C019', 'cname': '自然语言处理', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C013'},
        {'cno': 'C020', 'cname': '嵌入式系统与应用', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C009'},
        # 机器人工程
        {'cno': 'C021', 'cname': '自动控制原理', 'ccredit': 4, 'cteacher': fake.name(), 'cpno': 'C003'},
        {'cno': 'C022', 'cname': '机器人学导论', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C021'},
        {'cno': 'C023', 'cname': '传感器与检测技术', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C005'},
        {'cno': 'C024', 'cname': '工业机器人编程', 'ccredit': 3, 'cteacher': fake.name(), 'cpno': 'C022'}
    ]
    
    courses = []
    for c in course_list:
        courses.append(Course(**c))
    
    db.session.add_all(courses)
    db.session.commit()
    print(f"成功生成 {len(courses)} 门课程信息")

    # 导出课程 CSV
    csv_dir = os.path.join(os.path.dirname(__file__))
    with open(os.path.join(csv_dir, 'courses.csv'), 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['cno', 'cname', 'cpno', 'ccredit', 'cteacher']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for course in courses:
            writer.writerow({
                'cno': course.cno, 'cname': course.cname, 'cpno': course.cpno if course.cpno else '',
                'ccredit': course.ccredit, 'cteacher': course.cteacher
            })
    print("课程数据已导出到 courses.csv")

    # 2. 生成学生数据
    students = []
    dept_counters = {'数据科学与大数据技术': 1, '机器人工程': 1, '人工智能': 1}
    
    # 生成 1000 名学生
    for i in range(1000):
        sdept = random.choice(majors)
        if i == 0:
            students.append(Student(sno='2301610111', sname='杨静怡', ssex='女', sage=20, sdept='数据科学与大数据技术', hometown='江西省'))
            continue
            
        counter = dept_counters[sdept]
        if sdept == '数据科学与大数据技术':
            sno = f"230161{counter:04d}"
        elif sdept == '机器人工程':
            sno = f"230162{counter:04d}"
        else:
            sno = f"230163{counter:04d}"
        dept_counters[sdept] += 1
        
        # 避免和特例学号冲突
        if sno == '2301610111':
            sno = f"2301619999"

        students.append(Student(
            sno = sno, sname = fake.name(), ssex = random.choice(genders),
            sage = random.randint(18, 22), sdept = sdept, hometown = fake.province()
        ))
        
    db.session.add_all(students)
    db.session.commit()
    print(f"成功生成 {len(students)} 名学生信息")

    # 导出学生 CSV
    with open(os.path.join(csv_dir, 'students.csv'), 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['学号', '姓名', '性别', '年龄', '专业', '籍贯']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for student in students:
            writer.writerow({
                '学号': student.sno, '姓名': student.sname, '性别': student.ssex,
                '年龄': student.sage, '专业': student.sdept, '籍贯': student.hometown
            })
    print("学生数据已导出到 students.csv")

    # 3. 生成成绩数据
    all_students = Student.query.all()
    all_courses = Course.query.all()
    scores = []
    
    for student in all_students:
        # 每位学生随机选择 10-15 门课
        num_courses = random.randint(10, 15)
        selected_courses = random.sample(all_courses, num_courses)
        for course in selected_courses:
            # 挂科率控制在 8% 左右
            is_pass = random.random() > 0.08
            score_val = random.randint(60, 100) if is_pass else random.randint(0, 59)
            scores.append(Score(sno=student.sno, cno=course.cno, score=score_val))
            
    # 批量保存
    batch_size = 2000
    for i in range(0, len(scores), batch_size):
        db.session.add_all(scores[i:i+batch_size])
        db.session.commit()
    print(f"成功生成 {len(scores)} 条成绩记录")
    
    # 导出成绩 CSV
    with open(os.path.join(csv_dir, 'scores.csv'), 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['sno', 'cno', 'score']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for score in scores:
            writer.writerow({'sno': score.sno, 'cno': score.cno, 'score': score.score})
    print("成绩数据已导出到 scores.csv")

    print("数据导出完成。")

if __name__ == '__main__':
    with app.app_context():
        generate_data()
