# -*- coding: utf-8 -*-
"""
Created on Wed May 22 18:17:32 2024

@author: ashwe
"""

import logging as lg
import os, sys
import datetime as dt
import pytz
import requests


def send_to_telegram(message):
    TOKEN = ""
    chat_id = ""
    try:
        message = str(message)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        # requests.get(url).json() # this sends the message
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error(message)


class MyStreamHandler(lg.Handler):
    terminator = '\n'

    def __init__(self):
        lg.Handler.__init__(self)
        self.stream = sys.stdout

    def emit(self, record):
        if record.levelno == lg.INFO or record.levelno == lg.WARNING or record.levelno == lg.ERROR:
            try:
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
    # log_name = 'logger_file.log'
    currentlog_path = logs_path + log_name

    # log parameter
    lg.basicConfig(filename = currentlog_path, format = '%(asctime)s {%(pathname)s:%(lineno)d} [%(threadName)s] - %(levelname)s: %(message)s', level = lg.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

    # print the log in console
    console_formatter = lg.Formatter("%(asctime)s : %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = MyStreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # lg.getLogger().addHandler(lg.StreamHandler())
    lg.getLogger().addHandler(console_handler)

    # init message
    lg.info('Log initialized \n')
    send_to_telegram("Log initialized \n")