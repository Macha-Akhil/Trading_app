from flask import Flask,render_template, request ,jsonify,redirect, session,g
import logging,json,os
from kiteconnect import KiteConnect
from opertions import get_index_info,get_strike_lowprice,buy_stock,check_and_cancel_order,orderlist_check_placesell

#log details
logging.basicConfig(level=logging.DEBUG)
#kite instance
kite_api_key = "4kphycxxs6nm7ukf"
kite_api_secret = "4ucdchle2rn2of6r0vgsh0o15v2sm6kn"
kite_api_link = "https://kite.zerodha.com/connect/login?api_key=4kphycxxs6nm7ukf"
kite = KiteConnect(kite_api_key)
#register app
app = Flask(__name__,template_folder='templates',static_folder='static')
app.secret_key = os.urandom(24)
def get_kite_client():
    kite = KiteConnect(api_key=kite_api_key)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    return kite

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    request_token = request.args.get("request_token")
    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""
    kite = get_kite_client()
    data = kite.generate_session(request_token, api_secret=kite_api_secret)
    session["access_token"] = data["access_token"]
    return jsonify(access_token=data["access_token"])

@app.route('/tradestock', methods=['GET', 'POST'])
def main():
    try :
        if request.method == 'POST':
            #for key, value in request.form.items():
                #print(f'{key}: {value}')
            access_token = request.form.get('access_token')
            kite.set_access_token(access_token)
            dynamic_index = request.form.get('index')
            dynamic_xforindex = request.form.get('xforindex')
            dynamic_xforbuy = request.form.get('xforbuyprice')
            dynamic_xfortriggerprice_buy = request.form.get('xfortriggerprice_buy')
            dynamic_quantity = request.form.get('quantity')
            dynamic_xfor_add_up_sell = request.form.get('xfor_add_up_sell')
            dynamic_xfor_sub_down_sell = request.form.get('xfor_sub_down_sell')

        get_index = get_index_info(dynamic_index,access_token)
        #return str(get_index)
        if not isinstance(get_index, (int, float, complex)):
            raise ValueError(get_index)
        roundfig_openindex = round(get_index)
        if dynamic_index == "NIFTY 50":
            rounded_openindex = round(roundfig_openindex / 50 + 0.5) * 50
        elif dynamic_index == 'BANKNIFTY':
            rounded_openindex = round(roundfig_openindex / 100 + 0.5) * 100
        #return str(rounded_openindex)
        ce_strike = str(int(rounded_openindex) - int(dynamic_xforindex))
        pe_strike = str(int(rounded_openindex) + int(dynamic_xforindex))
        #response_data = {'ce_strike': ce_strike,'pe_strike': pe_strike}
        #return jsonify(response_data)
        #return [ce_strike,pe_strike]
        ce_strike_lp = get_strike_lowprice(dynamic_index,ce_strike,"CE",access_token)
        pe_strike_lp = get_strike_lowprice(dynamic_index,pe_strike,"PE",access_token)
        #return [ce_strike_lp,pe_strike_lp]
        ce_strike_lp.extend([dynamic_xforbuy,dynamic_xfortriggerprice_buy,dynamic_quantity])
        pe_strike_lp.extend([dynamic_xforbuy,dynamic_xfortriggerprice_buy,dynamic_quantity])
        #return [ce_strike_lp,pe_strike_lp]
        items_to_buy = [ce_strike_lp,pe_strike_lp]
        triggered_buy_data_ids = buy_stock(items_to_buy,access_token)
        #return triggered_buy_data_ids
        complete_order_dict = check_and_cancel_order(triggered_buy_data_ids,access_token)
        #return complete_order_dict
        sell_order_id = orderlist_check_placesell(complete_order_dict['average_price'],complete_order_dict['tradingsymbol'],complete_order_dict['quantity'],dynamic_xfor_add_up_sell,dynamic_xfor_sub_down_sell,access_token)
        return sell_order_id
        
    except Exception as e:
        return json.dumps({"Error in main_app.py":str(e)}),500

if __name__ == '__main__':
     app.run(port=5001,debug=True)
