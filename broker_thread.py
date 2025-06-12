# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 18:09:55 2025

@author: ashwe
"""

import threading
import queue
import time

from broker_angleone import *
from broker_aliceblue import *
from broker_stub import *

# from broker import *
from utils import *

# global thread_id
# thread_id = 0

class BrokerThread(threading.Thread):
    def __init__(self, broker):
        # global thread_id
        # thread_id = thread_id + 1
        # super().__init__(name=f"{broker}_{thread_id}")
        super().__init__()
        self.broker = None
        self.bkr_name = broker
        if self.bkr_name == "ANGELONE":
            self.broker = angleone()
        elif self.bkr_name == "ALICEBLUE":
            self.broker = aliceblue()
        elif self.bkr_name == "NOBROKER":
            self.broker = stub()

        # # self.broker = Broker(1, broker)  # Actual broker instance (e.g., AngleOneBroker)
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self._stop_event = threading.Event()

        lg.info(f"{self.bkr_name} broker thread start")
        lg.info(f"Broker = {self.broker}, type = {type(self.broker)}")
    
    def __del__(self):
        lg.info(f"{self.bkr_name} broker thread end")

    def run(self):
        lg.info(f"[{self.bkr_name} BrokerThread] Running...")
        while not self._stop_event.is_set():
            try:
                lg.info(f"[{self.bkr_name} BrokerThread] Running...")
                request_id, action, args = self.request_queue.get(timeout=20)
                lg.info(f"[{self.bkr_name} BrokerThread] Processing {action} with args {args}")
                if hasattr(self.broker, action):
                    method = getattr(self.broker, action)
                    result = method(*args)
                    self.response_queue.put((request_id, result))
                else:
                    self.response_queue.put((request_id, f"Unknown action: {action}"))
            except queue.Empty:
                continue
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))

    def stop(self):
        self._stop_event.set()
        del self.broker
        time.sleep(2)
        self.broker = None

    def send_request(self, action, *args):
        request_id = time.time()
        self.request_queue.put((request_id, action, args))
        return request_id

    def get_response(self, request_id, timeout=20):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res_id, result = self.response_queue.get(timeout=20)
                if res_id == request_id:
                    return result
                else:
                    self.response_queue.put((res_id, result))  # Put back unmatched
            except queue.Empty:
                continue
        lg.error("Timeout or No Response")
        return None
