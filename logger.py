# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:13:45 2024

@author: ashwe
"""

import logging as lg
import os, sys
import datetime as dt
import pytz

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Add custom log level
DONE = 25
lg.addLevelName(DONE, 'DONE')

def done(message, *args, **kwargs):
    """
    Global subdebug function to log messages at SUBDEBUG level.
    Uses the root logger.
    """
    root_logger = lg.getLogger()
    if root_logger.isEnabledFor(DONE):
        root_logger._log(DONE, message, args, **kwargs)


# Attach the global function to the logging module
lg.DONE = DONE
lg.done = done

class MyStreamHandler(lg.Handler):
    terminator = '\n'

    def __init__(self):
        lg.Handler.__init__(self)
        self.stream = sys.stdout

    def emit(self, record):
        if record.levelno == lg.INFO or record.levelno == lg.WARNING or record.levelno == lg.ERROR or record.levelno == lg.DONE:
            try:
                if record.levelno == lg.ERROR:
                    msg = bcolors.ERROR + self.format(record) + bcolors.ENDC
                elif record.levelno == lg.WARNING:
                    msg = bcolors.WARNING + self.format(record) + bcolors.ENDC
                elif record.levelno == lg.DONE:
                    msg = bcolors.OKGREEN + self.format(record) + bcolors.ENDC
                else:
                    msg = self.format(record)
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except RecursionError:
                raise
            except Exception:
                self.handleError(record)

def initialize_logger():
    # creating s folder for the log
    logs_path = './logs/'
    try:
        os.mkdir(logs_path)
    except OSError:
        print('Creation of the directory %s failed - it does not have to be bad' % logs_path)
    else:
        print('Succesfully created log directory')

    # renaming each log depending on time Creation
    date_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y%m%d_%H%M%S")
    log_name = 'logger_file_' + date_time + '.log'

    currentlog_path = logs_path + log_name

    # log parameter
    lg.basicConfig(filename = currentlog_path, format = '%(asctime)s {%(pathname)s:%(lineno)d} [%(threadName)s] - %(levelname)s: %(message)s', level = lg.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

    # print the log in console
    console_formatter = lg.Formatter("%(asctime)s : %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = MyStreamHandler()
    console_handler.setFormatter(console_formatter)
    
    lg.getLogger().addHandler(console_handler)

    # init message
    lg.info('Log initialized \n')
