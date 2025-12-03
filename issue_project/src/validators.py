"""
Input validation utilities
"""
import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format
    Returns: (is_valid, error_message)
    """
    if not email:
        return False, "邮箱不能为空"
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "邮箱格式不正确"
    
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 6:
        return False, "密码至少需要6个字符"
    
    if len(password) > 50:
        return False, "密码不能超过50个字符"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 2:
        return False, "用户名至少需要2个字符"
    
    if len(username) > 30:
        return False, "用户名不能超过30个字符"
    
    return True, ""
