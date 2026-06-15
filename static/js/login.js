// Helper function to switch tabs
function setActiveTab(tabId, loginDivId, disableFields, enableFields) {
    // Reset all tabs
    document.getElementById('snoTab').classList.remove('active');
    document.getElementById('phoneTab').classList.remove('active');
    document.getElementById('emailTab').classList.remove('active');
    
    // Hide all login methods
    document.getElementById('snoLogin').style.display = 'none';
    document.getElementById('phoneLogin').style.display = 'none';
    document.getElementById('emailLogin').style.display = 'none';
    
    // Activate clicked tab
    document.getElementById(tabId).classList.add('active');
    document.getElementById(loginDivId).style.display = 'block';
    
    // Set required / values
    enableFields.forEach(f => {
        const input = document.getElementById(f);
        if (input) input.required = true;
    });
    disableFields.forEach(f => {
        const input = document.getElementById(f);
        if (input) {
            input.required = false;
            input.value = ''; // Clear out other fields
        }
    });
    resetValidation();
}

// 切换登录方式
document.getElementById('snoTab').addEventListener('click', function() {
    setActiveTab('snoTab', 'snoLogin', ['phone', 'email'], ['sno']);
});

document.getElementById('phoneTab').addEventListener('click', function() {
    setActiveTab('phoneTab', 'phoneLogin', ['sno', 'email'], ['phone']);
});

document.getElementById('emailTab').addEventListener('click', function() {
    setActiveTab('emailTab', 'emailLogin', ['sno', 'phone'], ['email']);
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
    
    const snoTabActive = document.getElementById('snoTab').classList.contains('active');
    const phoneTabActive = document.getElementById('phoneTab').classList.contains('active');
    const snoInput = document.getElementById('sno');
    const phoneInput = document.getElementById('phone');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    
    if (snoTabActive) {
        if (!snoInput.value) {
            showError(snoInput, 'snoError', '请输入学号或工号');
            isValid = false;
        }
    } else if (phoneTabActive) {
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
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
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
    const phoneInput = document.getElementById('phone');
    if (emailInput && emailInput.value) {
        document.getElementById('emailTab').click();
    } else if (phoneInput && phoneInput.value) {
        document.getElementById('phoneTab').click();
    } else {
        document.getElementById('snoTab').click();
    }
});
