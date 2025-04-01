import os

NIFI_HOME = "/opt/nifi/nifi-current"
PYTHON_LOGGING_PATH = os.path.join(NIFI_HOME, "scripts")
PYTHON_LOGGING_FORMAT = '[%(asctime)s] [%(levelname)s] %(process)d, "%(filename)s", %(lineno)d, %(funcName)s : %(message)s'
PYTHON_LOGGING_MAX_SIZE = 10240000
PYTHON_LOGGING_BACKUP_COUNT = 9