class ValidationFailedError(Exception):
    def __init__(self, message):
        super().__init__(message)
        
class ServiceUnavailableError(Exception):
    def __init__(self, message):
        super().__init__(message)
    