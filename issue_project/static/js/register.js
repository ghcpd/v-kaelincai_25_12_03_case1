/**
 * Registration Form JavaScript
 * Handles form validation, submission, and UI feedback
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const form = document.getElementById('registerForm');
    const submitBtn = document.getElementById('submitBtn');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    
    // Get error message elements
    const usernameError = document.getElementById('usernameError');
    const emailError = document.getElementById('emailError');
    const passwordError = document.getElementById('passwordError');
    const globalError = document.getElementById('globalError');
    const globalErrorText = document.getElementById('globalErrorText');
    const successMessage = document.getElementById('successMessage');
    const successText = document.getElementById('successText');

    // Validation patterns
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    // Show error message
    function showError(input, errorElement, message) {
        input.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    // Clear error message
    function clearError(input, errorElement) {
        input.classList.remove('error');
        errorElement.textContent = '';
        errorElement.classList.remove('show');
    }

    // Show global error
    function showGlobalError(message) {
        globalErrorText.textContent = message;
        globalError.classList.add('show');
        successMessage.classList.remove('show');
    }

    // Show success message
    function showSuccess(message) {
        successText.textContent = message;
        successMessage.classList.add('show');
        globalError.classList.remove('show');
    }

    // Validate username
    function validateUsername() {
        const value = usernameInput.value.trim();
        
        if (!value) {
            showError(usernameInput, usernameError, '用户名不能为空');
            return false;
        }
        
        if (value.length < 2) {
            showError(usernameInput, usernameError, '用户名至少需要2个字符');
            return false;
        }
        
        if (value.length > 30) {
            showError(usernameInput, usernameError, '用户名不能超过30个字符');
            return false;
        }
        
        clearError(usernameInput, usernameError);
        return true;
    }

    // Validate email
    function validateEmail() {
        const value = emailInput.value.trim();
        
        if (!value) {
            showError(emailInput, emailError, '邮箱不能为空');
            return false;
        }
        
        if (!emailPattern.test(value)) {
            showError(emailInput, emailError, '邮箱格式不正确');
            return false;
        }
        
        clearError(emailInput, emailError);
        return true;
    }

    // Validate password
    function validatePassword() {
        const value = passwordInput.value;
        
        if (!value) {
            showError(passwordInput, passwordError, '密码不能为空');
            return false;
        }
        
        if (value.length < 6) {
            showError(passwordInput, passwordError, '密码至少需要6个字符');
            return false;
        }
        
        if (value.length > 50) {
            showError(passwordInput, passwordError, '密码不能超过50个字符');
            return false;
        }
        
        clearError(passwordInput, passwordError);
        return true;
    }

    // Add real-time validation
    usernameInput.addEventListener('blur', validateUsername);
    emailInput.addEventListener('blur', validateEmail);
    passwordInput.addEventListener('blur', validatePassword);

    // Clear global messages on input
    [usernameInput, emailInput, passwordInput].forEach(input => {
        input.addEventListener('input', () => {
            globalError.classList.remove('show');
            successMessage.classList.remove('show');
        });
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Clear previous messages
        globalError.classList.remove('show');
        successMessage.classList.remove('show');

        // Validate all fields
        const isUsernameValid = validateUsername();
        const isEmailValid = validateEmail();
        const isPasswordValid = validatePassword();

        if (!isUsernameValid || !isEmailValid || !isPasswordValid) {
            return;
        }

        // Disable submit button and show loading
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');

        try {
            // Prepare data
            const formData = {
                username: usernameInput.value.trim(),
                email: emailInput.value.trim(),
                password: passwordInput.value
            };

            // Send request
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Success
                showSuccess(data.message || '注册成功！');
                
                // Clear form (except email for user convenience)
                passwordInput.value = '';
                usernameInput.value = '';
                
                // Could redirect to login page after success
                // setTimeout(() => window.location.href = '/login', 2000);
            } else {
                // Error from server
                showGlobalError(data.error || '注册失败，请稍后重试');
                
                // Clear password for security
                passwordInput.value = '';
            }

        } catch (error) {
            console.error('Registration error:', error);
            showGlobalError('网络错误，请检查连接后重试');
            
            // Clear password for security
            passwordInput.value = '';
        } finally {
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.classList.remove('loading');
        }
    });
});
