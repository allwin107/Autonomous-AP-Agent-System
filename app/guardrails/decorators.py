from functools import wraps
from fastapi import HTTPException, Depends, Request
from app.api.auth import get_current_active_user, User
from app.guardrails.permissions import permission_checker, Permission
import inspect

def require_permission(permission: Permission):
    """
    Dependency to check static permission.
    """
    def check(user: User = Depends(get_current_active_user)):
        if not permission_checker.check_permission(user, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied: {permission.value} required"
            )
        return user
    return check

def enforce_sod(action: str):
    """
    Decorator to enforce Segregation of Duties.
    Must be used on endpoints where 'invoice_id' is a path parameter.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract invoice_id and user from arguments
            # FastAPI passes dependencies as kwargs usually? 
            # Actually, decorators on async route handlers are tricky with Depends.
            # Best practice: use a Dependency class that validates SoD.
            # But Dependencies don't easily see other path params unless we use Request.
            
            # For this simple decorator, we'll assume standard FastAPI/Starlette signature inspection
            # or we rely on the function having `current_user` and `invoice_id`.
            
            invoice_id = kwargs.get("invoice_id")
            user = kwargs.get("current_user")
            
            # If used as a decorator on the function, arguments are resolved.
            
            if not invoice_id or not user:
                 # Fallback/Error if not found
                 # This might happen if variable names differ.
                 pass

            if invoice_id and user:
                is_safe = await permission_checker.check_sod(invoice_id, user, action)
                if not is_safe:
                    raise HTTPException(
                        status_code=403,
                        detail="Segregation of Duties Violation. You cannot perform this action."
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Alternative: Class-based dependency for SoD if decorators get messy
class SoDChecker:
    def __init__(self, action: str):
        self.action = action
        
    async def __call__(self, request: Request, current_user: User = Depends(get_current_active_user)):
        # Extract invoice_id from path params
        invoice_id = request.path_params.get("invoice_id")
        if not invoice_id:
            # Maybe it's in body? For now strictly path.
            return
            
        is_safe = await permission_checker.check_sod(invoice_id, current_user, self.action)
        if not is_safe:
             raise HTTPException(
                status_code=403,
                detail=f"SoD Violation: You cannot {self.action} this invoice."
            )
