import feedparser
import yfinance as yf

ARTICLES = []
TRANSACTIONS = []

class Transaction:
    def __init__(self, t_id, action, t, market, ticker, quantity, price):
        self.t_id = t_id
        self.action = action
        self.action_time = t
        self.market = market
        self.ticker = ticker
        self.quantity = quantity
        self.price = price
    
    def __repr__(self):
        return f"{self.action}: {self.ticker} {self.quantity} x ${self.price}"

class Article:
    def __init__(self, a_id, action, t, t_str, tickers):
        self.a_id = a_id
        self.action = action
        self.date_published = t
        self.date_str = t_str
        self.tickers = tickers
    
    def __repr__(self):
        return self.action + ": " + ",".join(self.tickers)
    

def article_exists(a_id):
    for art in ARTICLES:
        if art.a_id == a_id:
            return True
    
    return False


def create_article(entry):
    action = None
    pub_time = None
    pub_str = None
    tickers = []

    pub_time = entry['published_parsed']
    year_str = pub_time[0]
    month_str = f"0{pub_time[1]}" if len(str(pub_time[1])) < 2 else pub_time[1]
    day_str = f"0{pub_time[2]}" if len(str(pub_time[2])) < 2 else pub_time[2]
    pub_str = f"{year_str}-{month_str}-{day_str}"

    content = entry['content']
    buy_count = 0
    sell_count = 0

    for c in content:
        for word in c['value'].split(" "):
            if "(" in word and ")" in word and ":" in word:
                # Check for ticker
                parts = word.split("(")[1]
                tick  = parts.split(")")[0]
                tickers.append(tick)
            else:
                # Check for sentiment
                if "buy" in word.lower():
                    buy_count += 1
                if "sell" in word.lower():
                    sell_count += 1
    
    if buy_count > sell_count:
        action = "BUY"
    elif sell_count > buy_count:
        action = "SELL"
    else:
        action = "HOLD"

    if action == None or pub_time == None or pub_str == None or tickers == []:
        return None
    
    return Article(entry['id'], action, pub_time, pub_str, tickers)


def complete_transactions(article):
    transaction_list = []

    tick_q = {}

    for t in article.tickers:
        if t in tick_q:
            tick_q[t] += 1
        else:
            tick_q[t] = 1
    
    for t in tick_q:
        market = t.split(":")[0]
        tick_str = "" 
        if market == "TSX":
            tick_str = ".TO"
        elif market == "TSXV":
            tick_str = ".V"
        else:
            break
        
        tick_str = t.split(":")[1] + tick_str
    
        tik = yf.Ticker(tick_str)

        hist = tik.history(period=article.date_str)

        if not hist.empty:
            day_low  = float(hist.at[article.date_str, 'Low'])
            day_high = float(hist.at[article.date_str, 'High'])

            p = (day_high + day_low) / 2

            print(p)

            trans = Transaction(0, article.action, article.date_str, market, tick_str, tick_q[t], p)
            transaction_list.append(trans)


    return transaction_list


def main():
    NewsFeed = feedparser.parse("https://www.fool.ca/feed/")

    for e in NewsFeed.entries:
        if not article_exists(e['id']):
            art = create_article(e)
            ARTICLES.append(art)
            if art == None:
                print("Error creating article.")
            else:
                print(art)

            if art.action != "HOLD":
                result = complete_transactions(art)
            
                for r in result:
                    TRANSACTIONS.append(r)
        else:
            print("Article exists already.")
    
    for tr in TRANSACTIONS:
        print(tr)
            


if __name__ == '__main__':
    main()