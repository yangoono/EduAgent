from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional

class LoginForm(FlaskForm):
    """LoginForm类 用户登录表单"""
    phone = StringField('手机号', validators=[Optional()])
    email = StringField('邮箱', validators=[Optional()])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, max=20, message='密码长度6-20位')
    ])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegisterForm(FlaskForm):
    """RegisterForm类 用户注册表单"""
    phone = StringField('手机号', validators=[
        Optional(),
        DataRequired(message='请输入手机号'),
        Regexp(r'^1[3-9]\d{9}$', message='手机号格式不正确'),
        Length(min=11, max=11, message='手机号必须11位')
    ])
    email = StringField('邮箱', validators=[
        Optional(),
        DataRequired(message='请输入邮箱'),
        Email(message='邮箱格式不正确'),
        Length(max=120, message='邮箱过长')
    ])
    name = StringField('真实姓名', validators=[
        DataRequired(message='请输入姓名')])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, max=20, message='密码长度6-20位')
    ])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码'),
        EqualTo('password', message='两次密码不一致')
    ])

    submit = SubmitField('注册')