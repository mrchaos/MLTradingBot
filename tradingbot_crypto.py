from lumibot.brokers import Alpaca
from lumibot.entities import Asset
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY") 
API_SECRET = os.getenv("ALPACA_SECRET_KEY") 
BASE_URL = os.getenv("ALPACA_API_URL")


ALPACA_CREDS = {
    "API_KEY":API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}

class MLTrader(Strategy): 
    def initialize(self, base_symbol:str="ETH",quote_symbol:str="USD", cash_at_risk:float=.5): 
        self.base_symbol = base_symbol
        self.quote_symbol = quote_symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self): 
        cash = self.get_cash() 
        yahoo_symbol=f"{self.base_symbol}-{self.quote_symbol}"
        last_price = self.get_last_price(yahoo_symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        # Alpaca crypto piar : {base}/{quote}
        alpaca_symbol=f"{self.base_symbol}/{self.quote_symbol}"
        news = self.api.get_news(symbol=alpaca_symbol, 
                                 start=three_days_prior,
                                 end=today)
        # news = [ev.__dict__["_raw"]["headline"] for ev in news]
        # news_headline = [ev.headline for ev in news]
        # probability_h, sentiment_h = estimate_sentiment(news_headline)
        news_summary = [ev.summary for ev in news]
        probability, sentiment = estimate_sentiment(news_summary)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        probability, sentiment = self.get_sentiment()
        if cash > last_price:
            if sentiment == "positive" and probability > .90: 
                if self.last_trade == "sell": 
                    self.sell_all()
                # Alpaca crypto piar : {base}/{quote}
                # alpaca_symbol=f"{self.base_symbol}/{self.quote_symbol}"
                order = self.create_order(
                    Asset(symbol=self.base_symbol, asset_type='crypto'), 
                    quantity, 
                    "buy", 
                    quote=Asset(symbol=self.quote_symbol, asset_type='crypto'),
                    type="market", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .90: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                # alpaca_symbol=f"{self.base_symbol}/{self.quote_symbol}"
                order = self.create_order(
                    Asset(symbol=self.base_symbol, asset_type='crypto'), 
                    quantity, 
                    "sell", 
                    quote=Asset(symbol=self.quote_symbol, asset_type='crypto'),
                    type="market", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"

start_date = datetime(2023,12,15)
end_date = datetime(2023,12,31) 
broker = Alpaca(ALPACA_CREDS) 
base = "ETH"
quote = "USD"
symbol_yahoo = f"{base}-{quote}"
symbol_alpaca = "ETH/USD"
benchmark_asset = Asset(symbol=symbol_yahoo, asset_type="crypto")
strategy = MLTrader(name='mlstrat',
                    quote_asset=Asset(symbol=quote, asset_type="crypto"),
                    broker=broker,
                    # parameters={"base_symbol":"ETH",
                    #             "quote_symbol":"USD",
                    #             "cash_at_risk":.5}
                    )
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    benchmark_asset=symbol_yahoo,
    quote_asset=Asset(symbol="USD", asset_type="crypto"),
    parameters={"base_symbol":"ETH",
                                "quote_symbol":"USD",
                                "cash_at_risk":.5}
)
# trader = Trader()
# trader.add_strategy(strategy)
# trader.run_all()
