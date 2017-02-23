import enum


@enum.unique
class ResponseStatus(enum.Enum):

    success = 1
    fail = 2


@enum.unique
class JobStatus(enum.Enum):

    success = 1
    fail = 2


@enum.unique
class JobCallbackResponseStatus(enum.Enum):

    success = 1
    fail = 2


@enum.unique
class TargetStatus(enum.Enum):

    init = 0
    success = 1
    fail = 2
    running = 3


@enum.unique
class TaskStatus(enum.Enum):

    init = 0
    success = 1
    fail = 2
    running = 3

