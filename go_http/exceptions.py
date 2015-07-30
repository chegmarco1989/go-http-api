""" Exceptions raised by API calls. """


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


class PagedException(Exception):
    """
    Exception raised during paged API calls that can be restarted by
    specifying a start cursor.

    Attributes:
        cursor - The value of the cursor for which the paged request failed.
        error - The exception that occurred.
    """
    def __init__(self, cursor, error):
        self.cursor = cursor
        self.error = error

    def __repr__(self):
        return "<PagedException cursor=%r error=%r>" % (
            self.cursor, self.error)

    def __str__(self):
        return repr(self)
