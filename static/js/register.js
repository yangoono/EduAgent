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

document.getElementById('toggleConfirmPassword').addEventListener('click', function() {
    const confirmPasswordInput = document.getElementById('password2');
    const icon = this;
    if (confirmPasswordInput.type === 'password') {
        confirmPasswordInput.type = 'text';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    } else {
        confirmPasswordInput.type = 'password';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    }
});

// 表单验证
document.getElementById('registerForm').addEventListener('submit', function(e) {
    let isValid = true;
    resetValidation();
    
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('password2');

    if (!nameInput.value.trim()) {
        showError(nameInput, 'nameError', '请输入用户名');
        isValid = false;
    } else if (nameInput.value.trim().length < 3 || nameInput.value.trim().length > 20) {
        showError(nameInput, 'nameError', '用户名长度3-20位');
        isValid = false;
    }


    if (!emailInput.value.trim()) {
        showError(emailInput, 'emailError', '请输入邮箱');
        isValid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
        showError(emailInput, 'emailError', '邮箱格式不正确');
        isValid = false;
    }
    if (!phoneInput.value.trim()) {
        showError(phoneInput, 'phoneError', '请输入手机号');
        isValid = false;
    } else if (!/^1[3-9]\d{9}$/.test(phoneInput.value.trim())) {
        showError(phoneInput, 'phoneError', '手机号格式不正确');
        isValid = false;
    }
    
    if (!passwordInput.value) {
        showError(passwordInput, 'passwordError', '请输入密码');
        isValid = false;
    } else if (passwordInput.value.length < 6 || passwordInput.value.length > 20) {
        showError(passwordInput, 'passwordError', '密码长度6-20位');
        isValid = false;
    }

    if (!confirmPasswordInput.value) {
        showError(confirmPasswordInput, 'confirmPasswordError', '请再次输入密码');
        isValid = false;
    } else if (passwordInput.value !== confirmPasswordInput.value) {
        showError(confirmPasswordInput, 'confirmPasswordError', '两次输入的密码不一致');
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