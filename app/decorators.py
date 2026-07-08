from functools import wraps
from flask import jsonify, request, current_app, g
from flask_login import current_user
import jwt

def jwt_required(f):
    """
    JWT Token 校验装饰器。
    如果请求头中没有 Token，则允许兼容读取 Flask-Login 的 Session（为了平滑过渡）。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
            
        if not token:
            # 兼容旧版的 session 登录
            if current_user.is_authenticated:
                g.current_user_role = current_user.role
                g.current_user_id = current_user.id
                g.current_sno = current_user.sno
                return f(*args, **kwargs)
            return jsonify({'success': False, 'message': '缺少 Token，未登录'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = data.get('user_id')
            g.current_user_role = data.get('role')
            g.current_sno = data.get('sno')
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token 已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': '无效的 Token'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """
    RBAC 权限校验装饰器，基于 JWT Payload 解析出的 g.current_user_role 或 session。
    可以传入多个角色，例如 @require_role('admin', 'teacher')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 首先确保已登录（由外层的 jwt_required 保证）
            user_role = getattr(g, 'current_user_role', None)
            
            if not user_role and current_user.is_authenticated:
                user_role = current_user.role
                
            if not user_role:
                return jsonify({'success': False, 'message': '未授权或未获取到角色'}), 401
                
            # admin 可以做所有事情
            if user_role not in roles and user_role != 'admin':
                return jsonify({'success': False, 'message': f'权限不足，需要 {roles} 权限'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
