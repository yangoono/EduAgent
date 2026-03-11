import random
import csv
from faker import Faker

from app import app, db
from app.models import Student, Course, Score


fake = Faker('zh_CN')

def generate_data():
    """生成模拟数据并插入数据库，然后导出到CSV文件"""

    # 清空现有数据
    db.drop_all()
    db.create_all()

    # 1. 生成100学生数据
    students = []
    majors = ['数据科学与大数据技术', '机器人工程', '人工智能']
    genders = ['男', '女']
    
    sdept_1 = 1
    sdept_2 = 1
    sdept_3 = 1

    for i in range(2, 101):
        sdept = random.choice(majors)
        if sdept == '数据科学与大数据技术':
            sno = f"23016101{sdept_1:02d}"
            sdept_1 += 1
        elif sdept == '机器人工程':
            sno = f"23016201{sdept_2:02d}"
            sdept_2 += 1
        else:
            sno = f"23016301{sdept_3:02d}"
            sdept_3 += 1

        if sno == '2301610111':
            students.append(Student(
                sno = '2301610111',
                sname = '杨静怡',
                ssex = '女',
                sage = 20, 
                sdept = '数据科学与大数据技术',
                hometown = '江西省'
            ))

        else:
            students.append(Student(
                sno = sno,
                sname = fake.name(),
                ssex = random.choice(genders),
                sage = random.randint(18, 25),
                sdept = sdept,
                hometown = fake.province()
            ))
    
    if students:
        with open('database\\students.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames =  ['学号', '姓名', '性别', '年龄', '专业', '籍贯']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for student in students:
                writer.writerow({
                    '学号': student.sno,
                    '姓名': student.sname,
                    '性别': student.ssex,
                    '年龄': student.sage,
                    '专业': student.sdept,
                    '籍贯': student.hometown
                })
        print("学生数据已导出到 students.csv")
    else:
        print("没有学生数据可导出。")
    db.session.add_all(students)
    db.session.commit()
    print("成功生成 100 名学生信息")
    
    # 2. 生成课程数据 
    courses = [
        Course(
            cno = 'C001', 
            cname ='高等数学',
            ccredit = 5,
            cteacher='张一',
            cpno = None 
        ),
        Course(
            cno = 'C002',
            cname ='线性代数',
            ccredit = 4, 
            cteacher='李二',
            cpno = 'C001' 
        ),
        Course(
            cno = 'C003',
            cname ='数据库原理与应用',
            ccredit = 4,
            cteacher='王三',
            cpno = None
        ),
        Course(
            cno = 'C004',
            cname ='计算机网络',
            ccredit = 3,
            cteacher='赵四',
            cpno = None
        ),
        Course(
            cno = 'C005',
            cname ='操作系统',
            ccredit = 4,
            cteacher='刘五',
            cpno = None
        ),
        Course(
            cno = 'C006',
            cname ='数据结构',
            ccredit = 5,
            cteacher='陈六',
            cpno = 'C001' 
        ),
        Course(
            cno = 'C007',
            cname ='大数据可视化',
            ccredit = 3,
            cteacher='孙七',
            cpno = 'C003' 
        ),
        Course(
            cno = 'C008',
            cname ='Python程序设计',
            ccredit = 3,
            cteacher='柯八',
            cpno = None
        )
    ]

    db.session.add_all(courses)
    db.session.commit()
    print("成功生成 8 门课程信息")

    if courses:
        with open('database\\courses.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['cno', 'cname', 'cpno', 'ccredit', 'cteacher']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for course in courses:
                writer.writerow({
                    'cno': course.cno,
                    'cname': course.cname,
                    'cpno': course.cpno,
                    'ccredit': course.ccredit,
                    'cteacher': course.cteacher
                })
        print("课程数据已导出到 courses.csv")
    else:
        print("没有课程数据可导出。")

    # 3. 生成成绩数据 
    all_students = Student.query.all()
    all_courses = Course.query.all() 
    scores = []

    for student in all_students:
        # 每位学生随机选择5-8门课
        num_courses = random.randint(5, 8)
        selected_courses = random.sample(all_courses, num_courses)
        
        for course in selected_courses:
            scores.append(Score(
                sno=student.sno,
                cno=course.cno,
                score=random.randint(55, 100) 
            ))
    
    db.session.add_all(scores)
    db.session.commit()
    print(f"成功生成 {len(scores)} 条成绩记录")
  
    # 导出成绩数据
    if scores:
        with open('database\\scores.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sno', 'cno', 'score']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for score in scores:
                writer.writerow({
                    'sno': score.sno,
                    'cno': score.cno,
                    'score': score.score
                })
        print("成绩数据已导出到 scores.csv")
    else:
        print("没有成绩数据可导出。")

    print("数据导出完成。")

if __name__ == '__main__':
    with app.app_context():
        generate_data()
