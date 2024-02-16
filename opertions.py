from flask import session,json
import kiteconnect
from datetime import datetime,time,timedelta
import time as sleep_time
import requests
from retrying import retry
# Replace these values with your API credentials
api_key = "kra4acx0471qmwqt"
def get_today_date():
        today_date = datetime.now().date()
        formatted_today_year = today_date.strftime("%Y,%#m,%#d")
        return formatted_today_year
def get_today_date_tdngsymbl():
        today_date = datetime.now().date()
        formatted_expiry = today_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
        return formatted_expiry
#function -- before 10am submitting the request with required data
def wait_until_market_open(target_time):
    current_time = datetime.now().time()
    while True:
        if current_time >= target_time:
            break
        sleep_time.sleep(5) 
        #print("hello world")  
        current_time = datetime.now().time()
# STEP - 1
# Morning 10Am or 1pm  NIFTY 50 or BANKNIFTY Index value
def get_index_info(indextime,indexname,access_token):
    try :
        if indextime == 10:
            indextime = 10
        elif indextime == 13:
            indextime = 13
        else:
            raise ValueError("get_index_info : We don't support other than 10AM & 1PM (13) time")
        #calling the function before the time to submit
        target_time = time(indextime,1)
        wait_until_market_open(target_time)
        kite = kiteconnect.KiteConnect(api_key, access_token)
        if indexname == "NIFTY 50":
            index = "NSE:NIFTY 50"
        elif indexname == "BANKNIFTY":
            index = "NSE:NIFTY BANK"
        else:
            raise ValueError("We don't support other than BANKNIFTY & NIFTY 50")
        # Get the quote for the Nifty50 and Bank_nifty index
        index_quote = kite.quote(index)
        index_instrument_token = str(index_quote[index]["instrument_token"])
        index_interval = "minute"
        today = get_today_date()
        year, month, day = today.split(",")
        # Create a datetime object representing the time at which you want to get the NIFTY 50 or BANKNIFTY index open price
        from_date_time = datetime(int(year),int(month),int(day),indextime,0,0)
        to_date_time = datetime(int(year),int(month),int(day),indextime,1,0)
        # Get the historical data for the NIFTY BANK or nifty 50 index
        index_historical_data = kite.historical_data(instrument_token=index_instrument_token,from_date=from_date_time,to_date=to_date_time,interval=index_interval)
        index_open =  index_historical_data[0]["open"]
        return index_open
    except Exception as e:
        return json.dumps({"Error in get_index_info":str(e)}),500
# STEP - 2
# Morning 10:01 - 10:04 min of low value of ( NIFTY 50 or BANKNIFTY ) CE AND PE values  
def get_strike_lowprice(indextime,indexname,strikeprice,option,access_token):
    try:
        if indextime == 10:
            indextime = 10
        elif indextime == 13:
            indextime = 13
        else:
            raise ValueError("get_strike_lowprice : We don't support other than 10AM & 1PM (13) time")
        #calling the function before the time to submit
        target_time = time(indextime,4)
        wait_until_market_open(target_time)
        kite = kiteconnect.KiteConnect(api_key, access_token)
        instruments = kite.instruments()
        today_expiry_date_str = get_today_date_tdngsymbl()
        today_expiry_date = datetime.strptime(today_expiry_date_str, "%a, %d %b %Y %H:%M:%S GMT")
        weekday = today_expiry_date.weekday()
        if indexname == "NIFTY 50":
            days_to_add = (3 - weekday) % 7
        elif indexname == "BANKNIFTY":
            days_to_add = (2 - weekday) % 7
        # Calculate the nearest weekday date
        nearest_weekday = today_expiry_date + timedelta(days=days_to_add)
        # Format the nearest weekday date as a string
        nearest_weekday_str = nearest_weekday.strftime("%a, %d %b %Y %H:%M:%S")
        option_interval = "minute"
        today = get_today_date()
        year, month, day = today.split(",")
        from_date_ts = datetime(int(year),int(month),int(day),indextime,0,0)
        to_date_ts = datetime(int(year),int(month),int(day),indextime,5,0)
        if indexname == "NIFTY 50":
            filtered_tradingsymbol = []
            for instrument in instruments:
                if instrument["tradingsymbol"].startswith("NIFTY") and strikeprice in instrument["tradingsymbol"] and instrument["tradingsymbol"].endswith(option):
                    filtered_tradingsymbol.append(instrument)
        elif indexname == "BANKNIFTY":
            filtered_tradingsymbol = []
            for instrument in instruments:
                if instrument["tradingsymbol"].startswith("BANKNIFTY") and strikeprice in instrument["tradingsymbol"] and instrument["tradingsymbol"].endswith(option):
                    filtered_tradingsymbol.append(instrument)
        dates =[]
        for date in filtered_tradingsymbol:
            expiry_date_str = date["expiry"].strftime("%a, %d %b %Y %H:%M:%S")
            if expiry_date_str == nearest_weekday_str:
                dates.append(date)
        get_tradingsymbol = dates[0]["tradingsymbol"]
        get_instrument_token = dates[0]["instrument_token"]
        index_historical_data_option = kite.historical_data(instrument_token=get_instrument_token,from_date=from_date_ts,to_date=to_date_ts,interval=option_interval)
        # Find the dictionary with the minimum "low" value
        min_low_entry_option = min(index_historical_data_option, key=lambda x: x["low"])
        low_value_option = min_low_entry_option["low"]
        roundfig_low_value_option = round(low_value_option)
        return [low_value_option,get_tradingsymbol]
        #return [roundfig_low_value_option,get_tradingsymbol]
        #return index_historical_data_option
    except Exception as e:
        return json.dumps({"Error in get_strike_lowprice":str(e)}),500   
# STEP - 3
# Trigger the CE AND PE values for buy        
def buy_stock(indextime,items_to_buy,access_token):
    try:
        if indextime == 10:
            indextime = 10
        elif indextime == 13:
            indextime = 13
        else:
            raise ValueError("buy_stock : We don't support other than 10AM & 1PM (13) time")
        target_time = time(indextime,5)
        wait_until_market_open(target_time)
        kite = kiteconnect.KiteConnect(api_key, access_token)
        triggered_data=[]
        orders_to_cancel = [] 
        for item in items_to_buy:
            buy_price = int(item[0]) + float(item[2])
            trigger_price = buy_price - float(item[3])
            try:
                order_id = kite.place_order(transaction_type=kite.TRANSACTION_TYPE_BUY,
                                        tradingsymbol=item[1],
                                        exchange=kite.EXCHANGE_NFO,
                                        quantity=int(item[4]),
                                        variety=kite.VARIETY_REGULAR,
                                        order_type=kite.ORDER_TYPE_SL,
                                        product=kite.PRODUCT_MIS,
                                        price=buy_price,
                                        trigger_price=trigger_price,
                                        validity=kite.VALIDITY_DAY)
                triggered_data.append(order_id)
                orders_to_cancel.append(order_id)
            except Exception as e:
                print(f"Error placing order for tradingsymbol: {item[1]} - {e}")
                for order_to_cancel in orders_to_cancel:
                    order_variety = "regular"
                    kite.cancel_order(variety=order_variety,order_id=order_to_cancel)
                return json.dumps({"Error in second buy_stock_": str(e)}), 500
        orders_to_cancel.clear()
        return triggered_data
    except Exception as e:
        return json.dumps({"Error in buy_stock":str(e)}),500
# STEP - 4 (SUB)
# If one stock ce or pe buy than other ce or pe get cancelled ( Below 4 functions for that:)   
# Function to check order status
@retry(wait_fixed=2000)
def check_order_status(order_id,access_token):
    try:
        kite = kiteconnect.KiteConnect(api_key, access_token)
        order_details = kite.order_history(order_id=order_id)
        for item in order_details:
            status = item['status']
            if status in ["COMPLETE", "REJECTED", "CANCELLED","TRIGGER PENDING"]:
                statuss = item      
        return statuss
    except Exception as e:
        return json.dumps({"Error in check_order_status":str(e)}),500
# STEP - 4 (SUB)
# Function to cancel another order (SELL) for a specific order ID
#@retry(wait_fixed=2000)
def cancel_other_order(order_id,access_token):
    try:
        kite = kiteconnect.KiteConnect(api_key, access_token)
        order_variety = "regular"
        existing_order_status = check_order_status(order_id,access_token)
        if existing_order_status['status'] == "TRIGGER PENDING":
            kite.cancel_order(variety=order_variety,order_id=order_id) 
    except Exception as e:
        return json.dumps({"Error in cancel_other_order":str(e)}),500
# STEP - 4 (SUB)
#List to store order statuses
#@retry(wait_fixed=2000)
def check_status(order_ids,access_token):
    try:
        for order_id in order_ids:
            order_status_details = check_order_status(order_id,access_token)
            if order_status_details['status'] == "COMPLETE":
                order_status_complete = order_status_details
                #Order successfully bought, now cancel the other order
                other_order_id = next(id for id in order_ids if id != order_status_details["order_id"])
                cancel_other_order(other_order_id,access_token) 
                return order_status_complete
    except Exception as e:
        return json.dumps({"Error in check_status":str(e)}),500
# STEP - 4   
#@retry(wait_fixed=2000)      
def check_and_cancel_order(order_ids,access_token):
    try:
        trigger_orders_cancel_time_str = "15:15"
        trigger_orders_cancel_time = time(*map(int, trigger_orders_cancel_time_str.split(':')))
        while True:
            order_status = check_status(order_ids,access_token)
            if order_status is not None:
                order_status_complete_data = order_status
                break
            current_time = datetime.now().time()
            if current_time >= trigger_orders_cancel_time:
                for order_info in order_ids:
                    cancel_other_order(order_info,access_token)
                return("Triggered orders are not buyed so At 3:15pm orders are cancelled.")
            sleep_time.sleep(2)
        return order_status_complete_data
    except Exception as e:
        return json.dumps({"Error in check_and_cancel_order":str(e)}),500
# STEP - 5 (SUB)    
# Sell the stock using details fetch live data (LTPDATA) and sell for up if graph goes up or sell for down if graph goes down  ( 3 functions used )
@retry(wait_fixed=1000)
def get_live_stock_price(symbol,access_token):
    try:
        kite = kiteconnect.KiteConnect(api_key, access_token)
        quote = kite.ltp("NFO:" + symbol)
        return quote["NFO:" + symbol]["last_price"]
    except Exception as e:
        return json.dumps({"Error in get_live_stock_price":str(e)}),500
# STEP - 5 (SUB)
# Sell the order 
#@retry(wait_fixed=1000)
def place_sell_order(tradingsymbol,quantity,access_token):
    kite = kiteconnect.KiteConnect(api_key, access_token)
    data_sell = []  
    try:
        order_id = kite.place_order(transaction_type=kite.TRANSACTION_TYPE_SELL,
                                    tradingsymbol=tradingsymbol,
                                    exchange=kite.EXCHANGE_NFO,
                                    quantity=quantity,
                                    variety=kite.VARIETY_REGULAR,
                                    order_type=kite.ORDER_TYPE_MARKET,
                                    product=kite.PRODUCT_MIS,
                                    validity=kite.VALIDITY_DAY)
        data_sell.append(order_id)
        return data_sell
    except Exception as e:
        return json.dumps({"Error in place_sell_order":str(e)}),500
# STEP - 5 
# Check sell the order graph is up or down 
#@retry(wait_fixed=1000)
def orderlist_check_placesell(average_price,tradingsymbol,quantity,dynamic_xfor_add_up_sell,dynamic_xfor_sub_down_sell,access_token):
    try:
        #kite = kiteconnect.KiteConnect(api_key, access_token)
        sell_for_up = average_price + float(dynamic_xfor_add_up_sell)
        sell_for_down = average_price - float(dynamic_xfor_sub_down_sell)
        sell_time_str = "15:15"
        sell_time = time(*map(int, sell_time_str.split(':')))
        sell_triggered = False
        sell_decreased_to = 10
        sell_decreased_value = sell_for_up - sell_decreased_to
        while True:
            live_price = get_live_stock_price(tradingsymbol,access_token)
            #sell_for_up is 130 if live price is 122 then sell_for_down should changes to 0.0
            if live_price >= sell_decreased_value:
                dynamic_xfor_sub_down_sell = 0.0
                sell_for_down = average_price - float(dynamic_xfor_sub_down_sell)
                #print("sell for down is 0.0")
            # Check if the graph goes up or goes down and trigger sell
            if live_price >= sell_for_up or live_price <= sell_for_down:
                sell_order_id = place_sell_order(tradingsymbol,quantity,access_token)
                break
            current_time = datetime.now().time()
            # Check if it's time to sell
            if current_time >= sell_time and not sell_triggered:
                sell_order_id = place_sell_order(tradingsymbol,quantity,access_token)
                sell_triggered = True
                return("buy orders are not sell so At 3:15pm orders are cancelled,due to market timing")
            sleep_time.sleep(1)
        return sell_order_id
    except Exception as e:
        return json.dumps({"Error in orderlist_check_placesell":str(e)}),500 
