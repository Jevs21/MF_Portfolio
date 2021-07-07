import feedparser
import sqlite3
import yfinance as yf
import sys


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
    

def get_article_ids():
    con = sqlite3.connect('database.db')
    cur = con.cursor()

    ids = []

    for row in cur.execute("SELECT * FROM articles"):
        ids.append(row[1])

    con.close()

    return ids


def add_article(art):
    con = sqlite3.connect('database.db')

    cur = con.cursor()
    cur.execute(f"INSERT INTO articles (a_id, action, date_published, date_str, tickers) VALUES ('{art.a_id}','{art.action}','{art.date_published}','{art.date_str}','{' '.join(art.tickers)}')")

    con.commit()
    con.close()


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


def add_transactions(transactions):
    con = sqlite3.connect('database.db')

    cur = con.cursor()

    # Create table
    for t in transactions:
        cur.execute(f"INSERT INTO transactions (action, action_time, market, ticker, quantity, price) VALUES ('{t.action}','{t.action_time}','{t.market}','{t.ticker}',{t.quantity},{t.price})")

    con.commit()
    con.close()


def get_transactions():
    con = sqlite3.connect('database.db')
    cur = con.cursor()

    trans = []

    # Create table
    for row in cur.execute(f"SELECT * FROM transactions"):
        trans.append(Transaction(row[0], row[1], row[2], row[3], row[4], row[5], row[6]))

    con.close()

    return trans


def main():
    NewsFeed = feedparser.parse("https://www.fool.ca/feed/")

    # Get ID list
    article_ids = get_article_ids()

    for e in NewsFeed.entries:
        if e['id'] not in article_ids:
            art = create_article(e)
            
            if art == None:
                print("Error creating article.")
            else:
                print(art)
                add_article(art)

            if art.action != "HOLD":
                result = complete_transactions(art)
                add_transactions(result)
        else:
            print("Article exists already.")
    
    for tr in TRANSACTIONS:
        print(tr)
            

def view_portfolio():
    trans = get_transactions()

    cash = 0.0
    holdings = {}
    markets = {}

    for t in trans:

        if t.action == "BUY":
            if t.ticker in holdings:
                # Total cost base
                new_cost = ((t.price * t.quantity) + (holdings[t.ticker]['price'] * holdings[t.ticker]['quantity'])) / (t.quantity + holdings[t.ticker]['quantity'])
                # new_cost = (t.price + holdings[t.ticker]['price']) / (t.quantity + holdings[t.ticker]['quantity'])
                # print(f"{t.price} + {holdings[t.ticker]['price']} / {t.quantity} + {holdings[t.ticker]['quantity']}")

                holdings[t.ticker]['quantity'] += t.quantity
                holdings[t.ticker]['price'] = new_cost
            else:
                holdings[t.ticker] = {
                    'quantity': t.quantity,
                    'price': t.price
                }
        elif t.action == "SELL":
            if t.ticker in holdings:
                if holdings[t.ticker][quantity] > 0:
                    q_sold = 0
                    holdings[t.ticker]['quantity'] -= t.quantity
                    if holdings[t.ticker]['quantity'] < 0:
                        q_sold = t.quantity - holdings[t.ticker]['quantity']
                    else:
                        q_sold = t.quantity
                    
                    cash += q_sold * holdings[t.ticker]['price']
                    holdings[t.ticker]['quantity'] = 0
            # else:
            #     holdings[t.ticker] = {
            #         'quantity': t.quantity,
            #         'price': t.price
            #     }

    for t in holdings:
        tik = yf.Ticker(t)
        # print(tik.info.keys())
        if "currentPrice" in tik.info:
            cur_price = tik.info['currentPrice']
            percent = ((cur_price - holdings[t]['price']) / holdings[t]['price']) * 100.0
            percent_str = f"({round(percent, 2)})" if percent < 0 else f"{round(percent, 2)}"

            price_str = "%.2f" % round(holdings[t]['price'], 2)
            cur_price_str = "%.2f" % round(cur_price, 2)

            holdings[t]['cur_price'] = cur_price
            
            print(f"{t}: {holdings[t]['quantity']} x ${price_str} -> {cur_price} %{percent_str}")
        else:
            print(f"Error getting current price of {t}.")
            holdings[t]['cur_price'] = 0.0
            holdings[t]['quantity'] = 0.0
            holdings[t]['price'] = 0.0
            # print(tik.info)
    
    book_total = 0.0
    cur_total = 0.0
    for t in holdings:
        book_total += (holdings[t]['quantity'] * holdings[t]['price'] )
        cur_total += (holdings[t]['quantity'] * holdings[t]['cur_price'] )
    
    pct_gain = ((cur_total - book_total) / book_total) * 100
    pct_gain_str = f"({round(pct_gain, 2)})" if pct_gain < 0 else f"{round(pct_gain, 2)}"

    print(f"# Portfolio Value: ${cur_total}  %{pct_gain_str}")



if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "view":
        view_portfolio()
    else:
        main()
