"""
Log specified Python imports to a file, remote machine or stderr.

What and how import are logged are controlled by the following environment
variables:

    * PYIMPORT_HANDLERS (optional): Any of 'file,stderr,server', csv
                    Defaults to 'file'
    * PYIMPORT_LOGFILE (optional): Filename to log imports.
    * PYIMPORT_HOST (optional/requires PORT):
                    Host to send UDP logging messages.
    * PYIMPORT_PORT (optional/requires HOST):
                    Port to send UDP logging messages.
    * PYIMPORT_LIBLIST (optional/stops logging if not provided):
                    A comma separated list of import names to log.
    * PYIMPORT_MSGFORMAT (optional): Format of logging message, {username} and
                    {import_name} will be expanded.
    * SINGULARITY_CONTAINER (required): Container name calling logger
    * PROJECTS_HOME (optional): Location where projects live
    * PYIMPORT_LOG_SUBDIR (optional): Directory below PROJECTS_HOME where
                    logs reside. Defaults to "datools/logs"

"""

import getpass
import logging
import os
import sys
from logging import FileHandler, StreamHandler
from logging.handlers import DatagramHandler
from datetime import date

# required outside class ? can't be in __init__ ?
logger = logging.getLogger('importlogger')

HOST = os.environ.get('PYIMPORT_HOST')
PORT = os.environ.get('PYIMPORT_PORT')

# replace 'debug' logic, allow empty 'LOGFILE' with default
HANDLERS = os.environ.get('PYIMPORT_HANDLERS', 'file')
HANDLERS = HANDLERS.lower().split(',')

# defaults to empty string --> empty list
LIBLIST = os.environ.get('PYIMPORT_LIBLIST', '')
MODULES_TO_LOG = LIBLIST.split(',')

# default format provided
JOBID = os.environ.get('PBS_JOBID')
DEFAULT_FORMAT = 'user:{username} import:{import_name}'
if JOBID is not None:
    DEFAULT_FORMAT += ' job:{job_id}'
MSG_FORMAT = os.environ.get('PYIMPORT_MSGFORMAT', DEFAULT_FORMAT)

PROJECTS_HOME = os.environ.get('PROJECTS_HOME')
LOG_SUBDIR = os.environ.get('PYIMPORT_LOG_SUBDIR','datools/logs')
# handle invalid/nonexistent directory (don't log)
LOG_LOCATION = None
if PROJECTS_HOME is not None and LOG_SUBDIR is not None:
    loc = PROJECTS_HOME+'/'+LOG_SUBDIR
    if os.path.isdir(loc):
        LOG_LOCATION = loc

# get logfile for writing to
USERNAME = getpass.getuser()
DATE = date.today().strftime('%Y%m%d')
CONTAINER = os.environ.get('SINGULARITY_CONTAINER')
# handle no logfile/no log location
LOGFILE = os.environ.get('PYIMPORT_LOGFILE')
if LOGFILE is None:
    if LOG_LOCATION is not None and CONTAINER is not None:
        LOGFILE = LOG_LOCATION+'/'+CONTAINER+'-'+USERNAME+'-'+DATE+'.log'
if LOGFILE is not None and not os.path.exists(LOGFILE):
    open(LOGFILE, 'a').close()
    if not os.access(LOGFILE, os.W_OK):
        LOGFILE = None

class ImportLogger(object):
    """ Log imports to strerr, a file or datagram. """

    def __init__(self):
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.logger = self.add_handlers(logger, formatter)
        import_name = "python"
        message = MSG_FORMAT.format(
            import_name=import_name,
            username=USERNAME,
            job_id=JOBID,
        )
        self.logger.info(message)

    def add_handlers(self, logger, formatter):
        for h in HANDLERS:
            handler = False
            if h == 'stderr':
                handler = StreamHandler()
            elif h == 'file':
                if LOGFILE is not None:
                    handler = FileHandler(filename=LOGFILE)
            elif h == 'server':
                if HOST is not None and PORT is not None:
                    handler = DatagramHandler(host=HOST, port=int(PORT))
            if handler is not False:
                handler.setLevel(logging.INFO)
                handler.setFormatter(formatter)
                logger.addHandler(handler)
        return(logger)
 
    # used in python>=3.4
    def find_spec(self, fullname, path=None, *args, **kwargs):
        if path is None:
            if fullname in MODULES_TO_LOG:
                import_name = fullname
                message = MSG_FORMAT.format(
                    import_name=import_name,
                    username=USERNAME,
                    job_id=JOBID,
                )
                self.logger.info(message)
        return None

    # find module defined for <=3.4
    find_module = find_spec


# register the import logger
sys.meta_path.insert(0, ImportLogger())
