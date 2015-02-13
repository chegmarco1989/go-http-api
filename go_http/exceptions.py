class UserOptedOutException(Exception):
    """
    Exception raised if a message is sent to a recipient who has opted out.

    Attributes:
        to_addr - The address of the opted out recipient
        message - The message content
        reason  - The error reason given by the API
    """
    def __init__(self, to_addr, message, reason):
        self.to_addr = to_addr
        self.message = message
        self.reason = reason
