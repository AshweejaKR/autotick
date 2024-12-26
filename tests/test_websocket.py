from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from SmartApi.smartWebSocketOrderUpdate import SmartWebSocketOrderUpdate
from SmartApi import SmartConnect
from pyotp import TOTP
import urllib
import sys, os
import json

main_path = 'C:/user/ashwee/autotick'
sys.path.append(main_path)
os.chdir(main_path)

from config import *
from angleone_broker import *


import threading

key_file = "angleone_key.txt"
API_KEY = get_keys(key_file)[0]
API_SECRET = get_keys(key_file)[1]
CLIENT_ID = get_keys(key_file)[2]
PASSWORD = get_keys(key_file)[3]
TOTP_TOKEN = get_keys(key_file)[4]

obj=SmartConnect(api_key=API_KEY)
totp = TOTP(TOTP_TOKEN).now()
data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
feed_token = obj.getfeedToken()

instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
response = urllib.request.urlopen(instrument_url)
instrument_list = json.loads(response.read())

global sws_message, stop, client, sws
sws_message = ""
stop = False
client = None

sws = SmartWebSocketV2(data["data"]["jwtToken"], API_KEY, CLIENT_ID, feed_token)
client = SmartWebSocketOrderUpdate(data["data"]["jwtToken"], API_KEY, CLIENT_ID, feed_token)

correlation_id = "stream_1" #any string value which will help identify the specific streaming in case of concurrent streaming
action = 1 #1 subscribe, 0 unsubscribe
mode = 3 #1 for LTP, 2 for Quote and 3 for SnapQuote

ticker1 = "INFY-EQ"
ticker2 = "SBIN-EQ"
exchange = "NSE"

token1 = token_lookup(ticker1, instrument_list, exchange)
token2 = token_lookup(ticker2, instrument_list, exchange)
token_list = [{"exchangeType": 1, "tokens": [token1, token2]}]

def on_data(wsapp, message):
    global sws_message, stop
    sws_message = message
    
    if stop:
        sys.exit()

def on_open(wsapp):
    print("on open")
    sws.subscribe(correlation_id, mode, token_list)

def on_error(wsapp, error):
    print(error)

def on_close(wsapp):
    print("on close")

def on_close(wsapp, close_status_code, close_msg):
    print("on close")

def run_smartWebSocketV2(sws):
    # Assign the callbacks.
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    sws.connect()

''' 
Sample SmartWebSocketV2 stream output
{'subscription_mode': 3, 'exchange_type': 1, 'token': '1594', 'sequence_number': 12109948, 'exchange_timestamp': 1735201464000,
'last_traded_price': 190735, 'subscription_mode_val': 'SNAP_QUOTE', 'last_traded_quantity': 3, 'average_traded_price': 190899, 
'volume_trade_for_the_day': 2129562, 'total_buy_quantity': 224305.0, 'total_sell_quantity': 246078.0, 
'open_price_of_the_day': 190905, 'high_price_of_the_day': 191975, 'low_price_of_the_day': 190230, 'closed_price': 190905, 
'last_traded_timestamp': 1735201464, 'open_interest': 78268800, 'open_interest_change_percentage': 4584350709158701777, 
'upper_circuit_limit': 209995, 'lower_circuit_limit': 171815, '52_week_high_price': 200645, '52_week_low_price': 135835, 
'best_5_buy_data': [{'flag': 1, 'quantity': 2, 'price': 190700, 'no of orders': 2}, {'flag': 1, 'quantity': 7, 'price': 190650, 
'no of orders': 1}, {'flag': 1, 'quantity': 47, 'price': 190645, 'no of orders': 3}, {'flag': 1, 'quantity': 103, 
'price': 190640, 'no of orders': 3}, {'flag': 1, 'quantity': 170, 'price': 190635, 'no of orders': 7}], 
'best_5_sell_data': [{'flag': 0, 'quantity': 43, 'price': 190735, 'no of orders': 3}, 
{'flag': 0, 'quantity': 83, 'price': 190740, 'no of orders': 3}, {'flag': 0, 'quantity': 99, 'price': 190745, 'no of orders': 2}, 
{'flag': 0, 'quantity': 205, 'price': 190750, 'no of orders': 6}, {'flag': 0, 'quantity': 354, 'price': 190755, 'no of orders': 9}]} 

'''

def run_SmartWebSocketOrderUpdate():
    global data, client
    client.on_close = on_close
    client.connect()

''' 
Sample SmartWebSocketOrderUpdate stream output
[I 241226 13:47:21 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:47:31 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:47:41 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:47:51 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:48:01 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:48:11 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:48:21 smartWebSocketOrderUpdate:32] Received message: b'\x00'
[I 241226 13:48:31 smartWebSocketOrderUpdate:32] Received message: b'\x00'

[I 241226 13:48:37 smartWebSocketOrderUpdate:32] Received message:
# for pending
{"user-id": "A496209","status-code": "200","order-status": "AB09","error-message": "","orderData": 
{"variety": "NORMAL","ordertype": "LIMIT","ordertag": "","producttype": "DELIVERY","price": 260.0,"triggerprice": 0.0,
"quantity": "1","disclosedquantity": "0","duration": "DAY","squareoff": 0.0,"stoploss": 0.0,"trailingstoploss": 0.0,
"tradingsymbol": "NIFTYBEES-EQ","transactiontype": "BUY","exchange": "NSE","symboltoken": "10576","instrumenttype": "",
"strikeprice": -1.0,"optiontype": "","expirydate": "","lotsize": "1","cancelsize": "0","averageprice": 0.0,
"filledshares": "0","unfilledshares": "1","orderid": "241226000761133","text": "","status": "open pending",
"orderstatus": "open pending","updatetime": "26-Dec-2024 13:48:37","exchtime": "","exchorderupdatetime": "",
"fillid": "","filltime": "","parentorderid": ""}}

# for completed
Received message: {"user-id": 
"A496209","status-code": "200","order-status": "AB05","error-message":
"","orderData": {"variety": "NORMAL","ordertype": "LIMIT","ordertag":
"","producttype": "DELIVERY","price": 266.94,"triggerprice": 0.0,"quantity":
"1","disclosedquantity": "0","duration": "DAY","squareoff": 0.0,"stoploss":
0.0,"trailingstoploss": 0.0,"tradingsymbol": "NIFTYBEES-EQ","transactiontype":
"BUY","exchange": "NSE","symboltoken": "10576","instrumenttype": "","strikeprice":
-1.0,"optiontype": "","expirydate": "","lotsize": "1","cancelsize":
"0","averageprice": 265.62,"filledshares": "1","unfilledshares": "0","orderid":
"241226000790638","text": "","status": "complete","orderstatus":
"complete","updatetime": "26-Dec-2024 14:07:19","exchtime": 
"26-Dec-2024 14:07:19","exchorderupdatetime": "26-Dec-2024 14:07:19",
"fillid": "","filltime": "","parentorderid": ""}}
'''

def display():
    global sws_message
    print(sws_message, "\n")
    # sym = symbol_lookup(sws_message['token'], instrument_list, exchange)
    # ltp = (sws_message['average_traded_price'] / 100 )
    # print("\n**** Tick: {} : LTP : {} **********".format(sym, ltp))
    # if sym == "INFY-EQ":
    #     print("**** Tick: {} : LTP : {} **********".format(sym, ltp))

threads = []
t1 = threading.Thread(target=run_smartWebSocketV2, args=(sws,))
threads.append(t1)
t2 = threading.Thread(target=run_SmartWebSocketOrderUpdate, args=())
threads.append(t2)

for th in threads:
    th.start()

time.sleep(3)

c = 0
while True:
    time.sleep(1)
    c = c + 1
    display()

    try:
        # TO STOP THE THREAD MANUALLY
        with open("../ltp.txt") as file:
            data = file.readlines()
            ltp = float(data[0])
            print(ltp, "\n")
            
            if ltp == 108:
                sws.unsubscribe(correlation_id, mode, token_list)
                sws.close_connection()
                client.close_connection()
                stop = True
                break

    except Exception as err: print(err)

for th in threads:
    th.join()

print("DONE EXECUTION")
