# Iron Condor Generator Program
import requests
from datetime import datetime, timedelta

# set up today
now = datetime.now()
date_today = str(now).split()[0]

# get this upcoming friday
days_until_friday = timedelta((4 - now.weekday()) % 7)
if str(days_until_friday)[0] == 0:
    duf = 7  # to make the code a bit simpler
    friday_date = now + timedelta(7)
else:
    duf = str(days_until_friday)[0]  # to make the code a bit simpler
    friday_date = now + days_until_friday
friday = str(friday_date).split()[0]

TICKER = input("What stock ticker would you like to use?: ").upper()  # can use this
# TICKER = "AAPL".upper()  # or this if you want to test the code

# from TD Ameritrade
CONSUMER_KEY = "YOUR OWN KEY HERE"  # not used for this API, but can be used for other Ameritrade APIs
API_KEY = "YOUR OWN API KEY"
endpoint = "https://api.tdameritrade.com/v1/marketdata/chains"  # the endpoint for this specific program
my_url = f"{endpoint}?apikey={API_KEY}&symbol={TICKER}"
TDA_LINK = f"https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=http://localhost&client_id" \
           f"={API_KEY}%40AMER.OAUTHAP "

stock_parameters = {
    "symbol": TICKER,
    "apikey": API_KEY,
    "strikeCount": 12,  # I found this value to work most of the time
    "fromDate": friday,
    "toDate": friday,  # can change this according to how far out you want the iron condor
}

# sets up the data set
response = requests.get(endpoint, params=stock_parameters)
response.raise_for_status()
stock_data = response.json()


# this starts the program
def start():
    # print(response.text)  # to get the JSON able to be viewed in a JSON viewer
    get_news()
    options = Options()
    options.sentiment()


# asks the user for news
def get_news():
    # for the news articles
    NEWS_API_KEY = "YOUR OWN NEWS API"
    NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"
    news_parameters = {
        "q": TICKER,
        "apiKey": NEWS_API_KEY,
    }

    # the following will give you the recent news on your selected ticker
    # helps form your opinion on how the market is doing
    news_response = requests.get(NEWS_ENDPOINT, params=news_parameters)
    news_response.raise_for_status()
    news_data = news_response.json()

    news_answer = input(f"Do you want news for {TICKER}? yes/no: ").lower()
    if news_answer == "yes":
        message = ""
        for _ in range(0, 3):
            if news_data["totalResults"] > _:
                message += str(news_data["articles"][_]["description"]) + "\n"
            elif news_data["totalResults"] == 0:
                message += f"There are no articles for {TICKER}."
                break
            else:
                message = None
        if message:
            print(message)
    else:
        pass

class Options:
    def __init__(self):
        self.upper_put_delta = -0.3
        self.lower_put_delta = -0.2
        self.upper_call_delta = 0.3
        self.lower_call_delta = 0.2
        self.gamma_value = 0.1  # I tested this to be accurate
        self.vega_value = 0.1  # I tested this to be accurate

    # this is what gives you the strike based on your sentiment, these are just my values
    def sentiment(self):  # upper means "upper range of risk", lower means the opposite

        sentiment_answer = input("How do you feel about the market? Bullish/Bearish/Neutral/Worried: ").lower()
        if sentiment_answer == "bullish":
            self.upper_put_delta = -0.35
            self. lower_put_delta = -0.2
            self.upper_call_delta = 0.2
            self.lower_call_delta = 0.1
        elif sentiment_answer == "bearish":
            self.upper_put_delta = -0.2
            self.lower_put_delta = -0.1
            self.upper_call_delta = 0.3
            self.lower_call_delta = 0.2
        elif sentiment_answer == "neutral":
            self.upper_put_delta = -0.25
            self.lower_put_delta = -0.15
            self.upper_call_delta = 0.25
            self.lower_call_delta = 0.15
        elif sentiment_answer == "worried":
            self.upper_put_delta = -0.15
            self.lower_put_delta = -0.1
            self.upper_call_delta = 0.15
            self.lower_call_delta = 0.1
            self.gamma_value = 0.08
            self.vega_value = 0.05
        else:
            pass
        self.greeks(self.upper_put_delta, self.lower_put_delta, self.upper_call_delta, self.lower_call_delta, self.gamma_value, self.vega_value)

    # gets the greeks for the iron condor options
    def greeks(self, upper_put_delta, lower_put_delta, upper_call_delta, lower_call_delta, gamma_value, vega_value):
        put_strike = None
        call_strike = None
        for _ in range(0, stock_parameters["strikeCount"]):
            # print("the _ is: " + str(_))
            option_types = ["call", "put"]
            for option_type in option_types:  # don't use theta for the weekly income model, but it can be incorporated
                delta = tuple(stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["delta"]
                gamma = tuple(stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["gamma"]
                # theta = tuple(stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["theta"]
                vega = tuple(stock_data[f"{option_type}ExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["vega"]
                if option_type == "put":
                    if self.get_short_put(upper_put_delta, lower_put_delta, delta, _) != 0 and \
                            gamma < gamma_value and vega < vega_value:
                        put_strike = self.get_short_put(upper_put_delta, lower_put_delta, delta, _)
                    else:
                        pass
                elif option_type == "call":  # can also be an "else" statement
                    if self.get_short_call(upper_call_delta, lower_call_delta, delta, _) != 0 and \
                            gamma < gamma_value and vega < vega_value:
                        call_strike = self.get_short_call(upper_call_delta, lower_call_delta, delta, _)
                    else:
                        pass
        if put_strike and call_strike:  # add the call_strike here
            print(f"\nThe strike price for the short put is: {put_strike}")
            print(f"The strike price for the short call is: {call_strike}")
        else:
            print(f"\nNot recommended to execute an iron condor for {TICKER} expiring on {friday}.")


    # gets the short put strike price
    def get_short_put(self, upper_put_delta, lower_put_delta, delta, _):
        if upper_put_delta < delta < lower_put_delta:
            strike = tuple(stock_data["putExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["strikePrice"]
        else:
            strike = 0
        return strike


    # gets the short call strike price
    def get_short_call(self, upper_call_delta, lower_call_delta, delta, _):
        if upper_call_delta > delta > lower_call_delta:
            strike = tuple(stock_data["callExpDateMap"][f"{friday}:{duf}"].items())[_][1][0]["strikePrice"]
        else:
            strike = 0
        return strike


# starts the main portion of the program
start()
