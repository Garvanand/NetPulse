class NetPulseException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundError(NetPulseException):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class ValidationError(NetPulseException):
    """Raised when domain validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=422)

class AuthenticationError(NetPulseException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, status_code=401)

class AuthorizationError(NetPulseException):
    """Raised when authorization fails."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)
