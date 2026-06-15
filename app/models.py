from app import db
# pyrefly: ignore [missing-import]
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

class Teacher(db.Model):
    __tablename__ = 'teachers'
    tno = db.Column(db.String(20), primary_key=True)
    tname = db.Column(db.String(50), nullable=False)
    tdept = db.Column(db.String(50), nullable=False)
    
    def to_dict(self):
        return {
            'tno': self.tno,
            'tname': self.tname,
            'tdept': self.tdept
        }

# Association table for User <-> Role
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# Association table for Role <-> Permission
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
        backref=db.backref('roles', lazy=True))

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    resource_path = db.Column(db.String(200), nullable=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) 
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='student') # admin, teacher, student (kept for backward compatibility)
    sno = db.Column(db.String(20), nullable=True) # 关联的学号或工号
    
    # New RBAC relationship
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
        backref=db.backref('users', lazy=True))
    
    __table_args__ = (
        db.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name='email_or_phone_required'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'

class KnowledgeDoc(db.Model):
    __tablename__ = 'knowledge_docs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=True) # 存储为JSON数组
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content
        }