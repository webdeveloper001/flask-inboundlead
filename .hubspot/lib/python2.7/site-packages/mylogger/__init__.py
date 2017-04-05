import logging

ml = None

loggers = {}
name = "mylogger"
log_level = logging.DEBUG
file_path = '/var/log/mylogger/{}.log'.format(name)
format = "%(created)s %(module)s %(funcName)s %(lineno)d %(message)s"

if not loggers.get(name):
    ml = logging.getLogger(name)
    ml.setLevel(log_level)
    handler = logging.FileHandler(file_path)
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    ml.addHandler(handler)
    loggers[name] = ml
else:
    ml = loggers[name]
