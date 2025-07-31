"""
Data validation utilities for Tatami framework.

This module provides comprehensive validation for input parameters based on type annotations.
"""

import inspect
from typing import Any, Union, get_origin, get_args
from pydantic import BaseModel, ValidationError
from starlette.responses import JSONResponse


class ValidationException(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, field_name: str, value: Any, expected_type: type, message: str = None):
        self.field_name = field_name
        self.value = value
        self.expected_type = expected_type
        self.message = message or f"Invalid value for {field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
        super().__init__(self.message)


def _is_optional_type(annotation) -> tuple[bool, type]:
    """
    Check if a type annotation is Optional (Union[T, None]).
    
    Returns:
        tuple: (is_optional, underlying_type)
    """
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        if len(args) == 2 and type(None) in args:
            # This is Optional[T] which is Union[T, None]
            underlying_type = args[0] if args[1] is type(None) else args[1]
            return True, underlying_type
    return False, annotation


def _validate_basic_type(value: Any, target_type: type, field_name: str, allow_none: bool = False) -> Any:
    """
    Validate and convert a value to the target type.
    
    Args:
        value: The value to validate
        target_type: The expected type
        field_name: Name of the field for error reporting
        allow_none: Whether None values are allowed for non-Optional types
        
    Returns:
        The validated and converted value
        
    Raises:
        ValidationException: If validation fails
    """
    # Handle None values
    if value is None:
        if target_type is type(None) or allow_none:
            return None
        raise ValidationException(field_name, value, target_type, f"{field_name} cannot be None")
    
    # Handle Any type - should accept any value as-is
    if target_type == Any:
        return value
    
    # Handle string inputs (common from HTTP requests)
    if isinstance(value, str):
        if target_type is str:
            return value
        elif target_type is int:
            try:
                return int(value)
            except (ValueError, TypeError) as e:
                raise ValidationException(field_name, value, target_type, 
                                        f"{field_name}: '{value}' is not a valid integer") from e
        elif target_type is float:
            try:
                return float(value)
            except (ValueError, TypeError) as e:
                raise ValidationException(field_name, value, target_type,
                                        f"{field_name}: '{value}' is not a valid float") from e
        elif target_type is bool:
            # Handle boolean conversion from string
            lower_value = value.lower()
            if lower_value in ('true', '1', 'yes', 'on'):
                return True
            elif lower_value in ('false', '0', 'no', 'off', ''):
                return False
            else:
                raise ValidationException(field_name, value, target_type,
                                        f"{field_name}: '{value}' is not a valid boolean")
        else:
            # Try direct conversion for other types
            try:
                return target_type(value)
            except (TypeError, ValueError) as e:
                raise ValidationException(field_name, value, target_type,
                                        f"{field_name}: Cannot convert '{value}' to {target_type.__name__}") from e
    
    # Handle non-string inputs
    if target_type == Any:
        return value
    
    # Check if the value is already the correct type
    if isinstance(value, target_type):
        return value
    
    # Try direct conversion
    try:
        return target_type(value)
    except (TypeError, ValueError) as e:
        raise ValidationException(field_name, value, target_type,
                                f"{field_name}: Cannot convert {type(value).__name__} to {target_type.__name__}") from e


def validate_parameter(value: Any, annotation: type, field_name: str, allow_none: bool = False) -> Any:
    """
    Validate a parameter value against its type annotation.
    
    Args:
        value: The value to validate
        annotation: The type annotation
        field_name: Name of the field for error reporting
        allow_none: Whether None values are allowed
        
    Returns:
        The validated and converted value
        
    Raises:
        ValidationException: If validation fails
    """
    # Handle missing annotation (assume Any)
    if annotation == inspect.Parameter.empty or annotation is None:
        annotation = Any
    
    # Check for Optional types
    is_optional, underlying_type = _is_optional_type(annotation)
    
    if is_optional and value is None:
        return None
    
    if value is None and not (is_optional or allow_none):
        raise ValidationException(field_name, value, annotation,
                                f"{field_name} is required but was not provided")
    
    # Use underlying type for Optional types
    target_type = underlying_type if is_optional else annotation
    
    # Handle Pydantic models
    if inspect.isclass(target_type) and issubclass(target_type, BaseModel):
        if isinstance(value, dict):
            try:
                return target_type(**value)
            except ValidationError as e:
                raise ValidationException(field_name, value, target_type,
                                        f"{field_name}: Pydantic validation failed: {e}") from e
        elif isinstance(value, target_type):
            return value
        else:
            raise ValidationException(field_name, value, target_type,
                                    f"{field_name}: Expected {target_type.__name__} or dict, got {type(value).__name__}")
    
    # Handle basic types
    return _validate_basic_type(value, target_type, field_name, allow_none)


def create_validation_error_response(error: ValidationException) -> JSONResponse:
    """
    Create a standardized error response for validation failures using RFC 7807 Problem Details format.
    
    Args:
        error: The validation exception
        
    Returns:
        JSONResponse with error details in RFC 7807 format
    """
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://datatracker.ietf.org/doc/html/rfc7807#section-3",
            "title": "Validation Error",
            "status": 422,
            "detail": f"Field '{error.field_name}' failed validation: {error.message}",
            "field": error.field_name,
            "input_value": error.value,
            "expected_type": error.expected_type.__name__ if hasattr(error.expected_type, '__name__') else str(error.expected_type),
            "field_path": error.field_name.split('.')
        },
        headers={"Content-Type": "application/problem+json"}
    )


def create_multiple_validation_errors_response(errors: list[ValidationException]) -> JSONResponse:
    """
    Create a response for multiple validation errors using RFC 7807 Problem Details format.
    
    Args:
        errors: List of validation exceptions
        
    Returns:
        JSONResponse with all error details in RFC 7807 format
    """
    # Create detailed information about each validation error
    validation_errors = []
    for error in errors:
        validation_errors.append({
            "field": error.field_name,
            "field_path": error.field_name.split('.'),
            "input_value": error.value,
            "expected_type": error.expected_type.__name__ if hasattr(error.expected_type, '__name__') else str(error.expected_type),
            "message": error.message
        })
    
    # Summary of all errors
    field_names = [error.field_name for error in errors]
    summary = f"Validation failed for {len(errors)} field(s): {', '.join(field_names)}"
    
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://datatracker.ietf.org/doc/html/rfc7807#section-3",
            "title": "Multiple Validation Errors",
            "status": 422,
            "detail": summary,
            "validation_errors": validation_errors,
            "total_errors": len(errors)
        },
        headers={"Content-Type": "application/problem+json"}
    )
