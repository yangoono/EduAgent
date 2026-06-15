import os
import sys
import random
import requests
from faker import Faker

# Add the project root directory to Python path so we can import 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from app.models import Student, Course, Score, User, KnowledgeDoc

fake = Faker('zh_CN')

def download_handbook():
    pdf_path = os.path.join(os.path.dirname(__file__), 'student_handbook.pdf')
    if not os.path.exists(pdf_path):
        print("Downloading SUSTech Student Handbook PDF...")
        print("For robust execution, please place a real PDF at database/student_handbook.pdf if desired.")
    return pdf_path

def seed_database():
    with app.app_context():
        print("Clearing existing data...")
        db.session.query(Score).delete()
        db.session.query(Course).delete()
        db.session.query(User).delete()
        db.session.query(Student).delete()
        db.session.query(KnowledgeDoc).delete()
        db.session.commit()

        print("Seeding Courses...")
        courses_data = [
            {'cno': 'C01', 'cname': '高等数学', 'ccredit': 4, 'cteacher': '张老师'},
            {'cno': 'C02', 'cname': '大学物理', 'ccredit': 3, 'cteacher': '李老师'},
            {'cno': 'C03', 'cname': 'Python程序设计', 'ccredit': 2, 'cteacher': '王老师'},
            {'cno': 'C04', 'cname': '数据库系统', 'ccredit': 3, 'cteacher': '赵老师'},
            {'cno': 'C05', 'cname': '人工智能导论', 'ccredit': 2, 'cteacher': '陈老师'},
        ]
        courses = []
        for c in courses_data:
            course = Course(cno=c['cno'], cname=c['cname'], ccredit=c['ccredit'], cteacher=c['cteacher'])
            db.session.add(course)
            courses.append(course)
        db.session.commit()

        print("Seeding Students and Users...")
        depts = ['计算机科学系', '软件工程系', '人工智能系', '网络安全系']
        students = []
        # Generate 200 students
        for i in range(1, 201):
            sno = f"2023{str(i).zfill(4)}"
            sname = fake.name()
            ssex = random.choice(['男', '女'])
            sage = random.randint(18, 22)
            sdept = random.choice(depts)
            hometown = fake.province()
            
            student = Student(sno=sno, sname=sname, ssex=ssex, sage=sage, sdept=sdept, hometown=hometown)
            db.session.add(student)
            students.append(student)

            # Create User account for the first 5 students for testing
            if i <= 5:
                user = User(
                    name=sname,
                    sno=sno,
                    email=fake.email(),
                    phone=fake.phone_number(),
                    role='student'
                )
                user.set_password('123456') # Default password
                db.session.add(user)
        
        # Add an admin user
        admin = User(name='Admin', email='admin@test.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        print("Seeding Scores...")
        for student in students:
            # Each student takes 3 to 5 courses
            num_courses = random.randint(3, 5)
            taken_courses = random.sample(courses, num_courses)
            for course in taken_courses:
                score_val = random.randint(60, 100)
                score = Score(sno=student.sno, cno=course.cno, score=score_val)
                db.session.add(score)
        db.session.commit()

        print("Seeding Knowledge Base...")
        from app.rag.pipeline import process_pdf, add_document
        pdf_path = os.path.join(os.path.dirname(__file__), 'student_handbook.pdf')
        if os.path.exists(pdf_path):
            print("Found student_handbook.pdf, parsing...")
            process_pdf(pdf_path, title_prefix="学生手册")
        else:
            print("student_handbook.pdf not found, using dummy text...")
            dummy_text = """
            学生手册总则
            第一条：学生必须遵守学校各项规章制度，按时出勤，不得无故旷课。
            第二条：每学期学生修满学分方可毕业。计算机专业毕业学分要求为120分。
            第三条：考试作弊者，将取消该门课程成绩，并记大过一次。
            第四条：学生宿舍晚上11点准时熄灯断电，严禁使用违章电器。
            第五条：图书馆借阅书籍逾期未还，将按每天0.1元收取滞纳金。
            """
            add_document("学生手册(内置)", dummy_text)
            
        print("Database seeding completed successfully!")
        for u in db.session.query(User).filter_by(role='student').limit(5):
            print(f" - Email: {u.email}, Sno: {u.sno}, Name: {u.name}")

if __name__ == '__main__':
    seed_database()
