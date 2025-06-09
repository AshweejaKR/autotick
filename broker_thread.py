# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 18:09:55 2025

@author: ashwe
"""

import threading
import queue
import time

from broker import *
from utils import *

class BrokerThread(threading.Thread):
    def __init__(self, broker):
        super().__init__()
        self.bkr_name = broker
        if self.bkr_name == "ANGELONE":
            self.broker = angleone()
        elif self.bkr_name == "ALICEBLUE":
            self.broker = aliceblue()
        elif self.bkr_name == "NOBROKER":
            self.broker = stub()

        # self.broker = Broker(1, broker)  # Actual broker instance (e.g., AngleOneBroker)
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self._stop_event = threading.Event()

        print(f"{self.bkr_name} broker thread start")
    
    def __del__(self):
        print(f"{self.bkr_name} broker thread end")

    def run(self):
        print("[{self.bkr_name} BrokerThread] Running...")
        while not self._stop_event.is_set():
            try:
                request_id, action, args = self.request_queue.get(timeout=1)
                print(f"[{self.bkr_name} BrokerThread] Processing {action} with args {args}")
                if hasattr(self.broker, action):
                    method = getattr(self.broker, action)
                    result = method(*args)
                    self.response_queue.put((request_id, result))
                else:
                    self.response_queue.put((request_id, f"Unknown action: {action}"))
            except queue.Empty:
                continue

    def stop(self):
        del self.broker
        self._stop_event.set()

    def send_request(self, action, *args):
        request_id = time.time()
        self.request_queue.put((request_id, action, args))
        return request_id

    def get_response(self, request_id, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res_id, result = self.response_queue.get(timeout=1)
                if res_id == request_id:
                    return result
                else:
                    self.response_queue.put((res_id, result))  # Put back unmatched
            except queue.Empty:
                continue
        return "Timeout or No Response"
