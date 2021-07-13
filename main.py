import dateutil.utils
from alice_blue import *
import conf
import logging
from datetime import datetime
import statistics
from time import sleep

def generate_key_token():
    try:
        access_token = AliceBlue.login_and_get_access_token(username=conf.username, password=conf.password, twoFA='a', api_secret=conf.app_secret, app_id=conf.app_id)
        alice = AliceBlue(username=conf.username, password=conf.password, access_token=access_token, master_contracts_to_download=['NSE', 'BSE', 'MCX', 'NFO'])
        return access_token, alice
    except:
        sleep(100)
        pass

logging.basicConfig(level=logging.DEBUG)
ltp = 0
EMA_CROSS_SCRIP = 'INFY'
NIFTY_BANK_IDX = ''
lots = 1
sl_percentage = 0.25 # exit if it goes more than 25% on either size of our straddle


def event_handler_quote_update(message):
    global ltp
    ltp = message['ltp']

def open_callback():
    global socket_opened
    socket_opened = True

def open_socket():
    global socket_opened
    socket_opened = False
    alice.start_websocket(subscribe_callback=event_handler_quote_update,socket_open_callback=open_callback,run_in_background=True)
    while (socket_opened == False):
        pass
    sleep(10)

def get_bank_nifty_month():
    global NIFTY_BANK_IDX,banknifty_script
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    current_month = datetime.now().month
    banknifty_script = None
    while banknifty_script == None:
        month = months[current_month-1]
        NIFTY_BANK_IDX = f"BANKNIFTY {month} FUT"
        banknifty_script = alice.get_instrument_by_symbol('NFO',NIFTY_BANK_IDX)

        current_month = current_month + 1
    print('final bnf', {banknifty_script})

def get_data_curr_expiry(atm_ce):
    global datecalc
    call = None
    datecalc = datetime.today()
    while call == None :
        try:
            call = alice.get_instrument_for_fno(symbol='BANKNIFTY', expiry_date= datecalc, is_fut= False, strike= atm_ce, is_CE= True)
            if call == None:
                print('No values in call')
                datecalc = datecalc + datetime.timedelta(days=1)
        except:
            pass

def sell_ce_option(bn_call,ce_price):
    quantity = lots*int(bn_call[5])

    sell_order = alice.place_order(transaction_type = TransactionType.Sell,
                     instrument = bn_call,
                     quantity = quantity,
                     order_type = OrderType.Market,
                     product_type = ProductType.Intraday,
                     price = 0.0,
                     trigger_price = None,
                     stop_loss = None,
                     square_off = None,
                     trailing_sl = None,
                     is_amo = False)
    sleep(1)
    if sell_order['status'] == 'success':
        sell_order = alice.place_order(transaction_type = TransactionType.Buy,
                     instrument = bn_call,
                     quantity = quantity,
                     order_type = OrderType.StopLossMarket,
                     product_type = ProductType.Intraday,
                     price = 0.0,
                     trigger_price = 1.5*ce_price,
                     stop_loss = None,
                     square_off = None,
                     trailing_sl = None,
                     is_amo = False)

def sell_pe_option(bn_put,pe_price):
    quantity = lots * int(bn_put[5])

    sell_order = alice.place_order(transaction_type=TransactionType.Sell,
                                   instrument=bn_put,
                                   quantity=quantity,
                                   order_type=OrderType.Market,
                                   product_type=ProductType.Intraday,
                                   price=0.0,
                                   trigger_price=None,
                                   stop_loss=None,
                                   square_off=None,
                                   trailing_sl=None,
                                   is_amo=False)
    sleep(1)
    if sell_order['status'] == 'success':
        sell_order = alice.place_order(transaction_type=TransactionType.Buy,
                                       instrument=bn_put,
                                       quantity=quantity,
                                       order_type=OrderType.StopLossMarket,
                                       product_type=ProductType.Intraday,
                                       price=0.0,
                                       trigger_price=1.5 * pe_price,
                                       stop_loss=None,
                                       square_off=None,
                                       trailing_sl=None,
                                       is_amo=False)

def get_ce_curr_price(atm_ce):
    global bn_call,token_ce,ce_order_placed, ce_sl_price
    bn_call = alice.get_instrument_for_fno(symbol='BANKNIFTY', expiry_date= datecalc, is_fut=False, strike= atm_ce,is_CE=True)
    alice.subscribe(bn_call,LiveFeedType.COMPACT)
    sleep(1)
    ce_price=ltp
    sell_ce_option(bn_call,ce_price)

    print('Sell ce order placed at: {ltp}')
    alice.unsubscribe(bn_call,LiveFeedType.COMPACT)

def get_pe_curr_price(atm_pe):
    global bn_put,token_pe,pe_order_placed,pe_sl_price
    bn_put = alice.get_instrument_for_fno(symbol='BANKNIFTY', expiry_date=datecalc, is_fut=False, strike=atm_pe,
                                           is_CE= False)
    alice.subscribe(bn_put, LiveFeedType.COMPACT)
    sleep(1)
    pe_price = ltp
    sell_pe_option(bn_put, pe_price)

    print('Put pe order placed at: {ltp}')
    alice.unsubscribe(bn_put, LiveFeedType.COMPACT)


if __name__ == '__main__':
    global socket_opened, bn_call, order_placed, ce_price, pe_price
    socket_opened = False
    access_token, alice = generate_key_token()
    if socket_opened == False:
        open_socket()
    get_bank_nifty_month()

    alice.subscribe(banknifty_script,LiveFeedType.MARKET_DATA)
    sleep(10)

    order_placed = False

    while datetime.now().time() <= time(9,30):
        sleep(60)
    try:
        while order_placed == False:
            curr_ltp = ltp
            atm_ce,atm_pe = int(curr_ltp/100)*100, int(curr_ltp/100)*100
            alice.unsubscribe(banknifty_script, LiveFeedType.MARKET_DATA)
            get_data_curr_expiry(atm_ce)
            get_ce_curr_price(atm_ce)
            get_pe_curr_price(atm_pe)
            order_placed = True
    except Exception as e:
        print(e)




