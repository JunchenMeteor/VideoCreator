"""Stable failures; provider exception bodies and secrets never become public errors."""


class EngineError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409, retryability: str = "never"):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryability = retryability
