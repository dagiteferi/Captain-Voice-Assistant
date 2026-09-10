class DomainError(Exception):
    pass


class UngroundedAnswerError(DomainError):
    pass


class MissingVoiceProfileError(DomainError):
    pass


class InvalidCommandTransition(DomainError):
    pass


class InvalidSubmissionTransition(DomainError):
    pass
