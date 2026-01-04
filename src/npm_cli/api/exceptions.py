"""Custom exceptions for NPM API operations.

This module defines a hierarchy of exceptions for handling NPM API errors
with proper context preservation for debugging and user-friendly error messages.
"""

import httpx
from pydantic import ValidationError


class NPMAPIError(Exception):
    """Base exception for NPM API errors.

    Stores optional httpx.Response for detailed error context including
    status code and response body for debugging.

    Attributes:
        response: Optional httpx.Response object from failed request
    """

    def __init__(self, message: str, response: httpx.Response | None = None):
        """Initialize API error with message and optional response.

        Args:
            message: Human-readable error description
            response: Optional httpx.Response from failed request
        """
        super().__init__(message)
        self.response = response

    def __str__(self) -> str:
        """Format error message with status code if response available."""
        message = super().__str__()
        if self.response is not None:
            return f"{message} (HTTP {self.response.status_code})"
        return message


class NPMConnectionError(NPMAPIError):
    """Exception for NPM connection failures.

    Raised when the NPM API cannot be reached (connection refused, timeout, etc.).
    Indicates network-level problems rather than application-level errors.
    """

    def __init__(self, message: str):
        """Initialize connection error with helpful message.

        Args:
            message: Description of connection failure including URL if available
        """
        super().__init__(message, response=None)


class NPMValidationError(NPMAPIError):
    """Exception for schema validation failures.

    Raised when NPM API response doesn't match expected Pydantic schema,
    indicating potential API changes or version incompatibility.

    Attributes:
        validation_error: Optional original Pydantic ValidationError
    """

    def __init__(
        self,
        message: str,
        validation_error: ValidationError | None = None
    ):
        """Initialize validation error with optional Pydantic error.

        Args:
            message: Human-readable error description
            validation_error: Optional Pydantic ValidationError with details
        """
        super().__init__(message, response=None)
        self.validation_error = validation_error

    def __str__(self) -> str:
        """Format error message with validation details if available."""
        message = super().__str__()
        if self.validation_error is not None:
            # Include key validation details for debugging
            error_details = str(self.validation_error)
            # Truncate if too long for console output
            if len(error_details) > 200:
                error_details = error_details[:200] + "..."
            return f"{message}\nValidation details: {error_details}"
        return message
