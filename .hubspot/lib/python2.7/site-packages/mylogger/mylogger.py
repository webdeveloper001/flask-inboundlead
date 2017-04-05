import logging

loggers = {}


def ml(name=None, file_path=None, log_level=None):
    global loggers

    if not name:
        name = "mylogger"

    if not log_level:
        log_level = logging.DEBUG

    if not file_path:
        file_path = '/var/log/mylogger/{}.log'.format(name)

    if not loggers.get(name):
        ml = logging.getLogger(name)
        ml.setLevel(log_level)
        handler = logging.FileHandler(file_path)
        format = "%(created)s %(module)s %(funcName)s %(lineno)d %(message)s"
        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        ml.addHandler(handler)
        loggers[name] = ml
    else:
        ml = loggers[name]

    return ml
