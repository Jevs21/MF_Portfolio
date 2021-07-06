# MF_Portfolio
Lets see how foolish they really are....

## Program Flow

1. Retrieve RSS feed from Motley Fool
2. Check for any new articles
    - Articles' IDs will be stored so they can only be analyzed once
3. If a new article is found parse article
    - Analyze if article sentiment is to buy, sell or hold.
4. If bullish, purchase 1 share of each ticker mentioned in the article.
    - E.g. if the ticker BB occurs 5 times in the article, 5 shares will be purchased.
    - The purchase price will be the time the article was published.
5. If bearish, sell 1 share of any ticker mentioned in the article - if shares of said tickers exist in your portfolio.
6. If hold, do nothing.

## Database Architecture

Articles Table:
- article_id
- date_published
- action (BUY/SELL/HOLD)
- tickers

Transactions Table:
- id
- article_id
- action (BUY/SELL)
- action_time
- ticker
- quantity
