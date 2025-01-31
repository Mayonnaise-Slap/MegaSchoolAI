class LLMWorkflowError(Exception):
    """Exception raised when the LLM workflow critically fails and needs to restart."""
    def __init__(self, message="LLM workflow encountered a critical failure and needs to restart"):
        super().__init__(message)
