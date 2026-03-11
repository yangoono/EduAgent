from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Student(db.Model):
    __tablename__ = 'students'
    sno = db.Column(db.String(20), primary_key=True)
    sname = db.Column(db.String(50), nullable=False) 
    ssex = db.Column(db.String(2), nullable=False, default='男') 
    sage = db.Column(db.Integer, nullable=False) 
    sdept = db.Column(db.String(50), nullable=False) 
    hometown = db.Column(db.String(50), nullable=False) 

    scores = db.relationship('Score', backref='student', lazy=True) 

    __table_args__ = (
        db.CheckConstraint("ssex IN ('男', '女')", name='ssex_check'),
        db.CheckConstraint("sage > 0 AND sage < 100", name='sage_check'), 
    )

    def to_dict(self):
        return {
            'sno': self.sno,
            'sname': self.sname,
            'sage': self.sage,
            'ssex': self.ssex,
            'sdept': self.sdept,
            'hometown': self.hometown
        }

class Course(db.Model):
    __tablename__ = 'courses'
    cno = db.Column(db.String(20), primary_key=True)
    cname = db.Column(db.String(50), nullable=False) 
    cpno = db.Column(db.String(20), db.ForeignKey('courses.cno')) 
    ccredit = db.Column(db.Integer, nullable=False) 
    cteacher = db.Column(db.String(50), nullable=False)

    scores = db.relationship('Score', backref='courses', lazy=True) 
    prerequisite_course = db.relationship(
        'Course',
        remote_side=[cno], 
        backref=db.backref('dependent_courses', lazy=True), 
        uselist=False 
    )

    def to_dict(self):
        return {
            'cno': self.cno,
            'cname': self.cname,
            'cpno': self.cpno,
            'ccredit': self.ccredit,
            'cteacher': self.cteacher
        }
    
class Score(db.Model):
    __tablename__ = 'score'
    sno = db.Column(db.String(20), db.ForeignKey('students.sno'), primary_key=True) # 学号
    cno = db.Column(db.String(20), db.ForeignKey('courses.cno'), primary_key=True) # 课程号
    score = db.Column(db.Integer) # 成绩
    
    __table_args__ = (
        db.UniqueConstraint('sno', 'cno', name='_sno_cno_uc'),
    )

    def to_dict(self):
        return {
            'sno': self.sno,
            'cno': self.cno,
            'score': self.score
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) 
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    
    __table_args__ = (
        db.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name='email_or_phone_required'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'