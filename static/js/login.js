
// 切换登录方式
document.getElementById('phoneTab').addEventListener('click', function() {
    this.classList.add('active');
    document.getElementById('emailTab').classList.remove('active');
    document.getElementById('phoneLogin').style.display = 'block';
    document.getElementById('emailLogin').style.display = 'none';
    document.getElementById('phone').required = true;
    document.getElementById('email').required = false;
    resetValidation();
});

document.getElementById('emailTab').addEventListener('click', function() {
    this.classList.add('active');
    document.getElementById('phoneTab').classList.remove('active');
    document.getElementById('emailLogin').style.display = 'block';
    document.getElementById('phoneLogin').style.display = 'none';
    document.getElementById('email').required = true;
    document.getElementById('phone').required = false;
    resetValidation();
});

// 显示/隐藏密码
document.getElementById('togglePassword').addEventListener('click', function() {
    const passwordInput = document.getElementById('password');
    const icon = this;
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    }
});

// 表单验证
document.getElementById('loginForm').addEventListener('submit', function(e) {
    let isValid = true;
    resetValidation();
    
    // 检查手机号或邮箱是否填写
    const phoneTabActive = document.getElementById('phoneTab').classList.contains('active');
    const phoneInput = document.getElementById('phone');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    
    if (phoneTabActive) {
        if (!phoneInput.value) {
            showError(phoneInput, 'phoneError', '请输入手机号');
            isValid = false;
        } else if (!/^1[3-9]\d{9}$/.test(phoneInput.value)) {
            showError(phoneInput, 'phoneError', '手机号格式不正确');
            isValid = false;
        }
    } else {
        if (!emailInput.value) {
            showError(emailInput, 'emailError', '请输入邮箱');
            isValid = false;
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value)) {
            showError(emailInput, 'emailError', '邮箱格式不正确');
            isValid = false;
        }
    }
    
    // 检查密码
    if (!passwordInput.value) {
        showError(passwordInput, 'passwordError', '请输入密码');
        isValid = false;
    } else if (passwordInput.value.length < 6 || passwordInput.value.length > 20) {
        showError(passwordInput, 'passwordError', '密码长度6-20位');
        isValid = false;
    }
    
    if (!isValid) {
        e.preventDefault();
    }
});

function showError(input, errorElementId, message) {
    input.classList.add('is-invalid');
    const errorElement = document.getElementById(errorElementId);
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

function resetValidation() {
    document.querySelectorAll('.is-invalid').forEach(el => {
        el.classList.remove('is-invalid');
    });
    document.querySelectorAll('.invalid-feedback').forEach(el => {
        el.style.display = 'none';
    });
}

// 根据初始值自动选择标签页
document.addEventListener('DOMContentLoaded', function() {
    const emailInput = document.getElementById('email');
    if (emailInput && emailInput.value) {
        document.getElementById('emailTab').click();
    }
});
