# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:13:45 2024

@author: ashwe
"""

import logging as lg
import os, sys
import datetime as dt
import pytz

import gvars

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

def myPrint(msg):
    if gvars.debugOn:
        print(msg)

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

def log_error():
    """
    Enhanced error logging function that captures full traceback and stack trace
    """
    import traceback
    import datetime as dt
    import io

    # Create error logs directory if it doesn't exist
    error_logs_path = './logs/tracedata/'
    try:
        os.makedirs(error_logs_path, exist_ok=True)
    except OSError as e:
        lg.error(f'Error creating error_logs directory: {e}')
        return

    # Create error log file with timestamp
    timestamp = dt.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y%m%d_%H%M%S")
    error_log_file = f'{error_logs_path}error_trace_{timestamp}.log'

    try:
        # Use StringIO to capture the error details
        error_details = io.StringIO()
        error_details.write("="*60 + "\n")
        error_details.write("Exception Traceback:\n")
        traceback.print_exc(file=error_details)
        error_details.write("="*60 + "\n")
        error_details.write("\n" + "="*60 + "\n")

        # Get stack trace
        error_details.write("Stack Trace:\n")
        error_details.write("="*60 + "\n")
        traceback.print_stack(file=error_details)
        error_details.write("="*60 + "\n")

        # Get the complete error details
        error_text = error_details.getvalue()
        error_details.close()

        # Write to file
        with open(error_log_file, 'w') as f:
            f.write(error_text)

        # Log through lg.error
        lg.error("\n" + error_text)

    except Exception as e:
        lg.error(f"Failed to write error log: {e}")
