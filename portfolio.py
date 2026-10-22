"""Stock Portfolio Performance Tracker

- Validates tickers against the S&P 500 dataset (sp500.csv)
- Fetches live prices with yfinance (falls back to manual entry)
- Logs results to portfolio_summary.csv
"""
import csv
import os
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

TICKER_FILE = "sp500.csv"
SUMMARY_FILE = "portfolio_summary.csv"


def load_tickers(path):
    """Return dict: SYMBOL -> company name from the S&P 500 dataset."""
    tickers = {}
    if not os.path.exists(path):
        print(f"[!] '{path}' not found. Ticker validation is off.")
        return None
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            symbol = (row.get("Symbol") or "").strip().upper()
            if symbol:
                tickers[symbol] = (row.get("Security") or "").strip()
    return tickers


def read_positive(prompt, cast):
    while True:
        try:
            value = cast(input(prompt))
            if value > 0:
                return value
            print("  Must be greater than 0.")
        except ValueError:
            print("  Invalid number, try again.")


def get_price(ticker):
    """Live price via yfinance; ask the user if that fails."""
    if yf is not None:
        try:
            hist = yf.Ticker(ticker.replace(".", "-")).history(period="5d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        print(f"  [!] Couldn't fetch live price for {ticker}.")
    else:
        print("  [!] yfinance not installed (pip install yfinance).")
    return read_positive("  Enter current price manually: ", float)


def collect_portfolio(tickers):
    """Return dict: ticker -> {name, buy_price, shares, current_price}"""
    portfolio = {}
    print("Enter your holdings. Type 'done' as ticker to finish.\n")
    while True:
        ticker = input("Ticker: ").strip().upper()
        if ticker == "DONE":
            break
        if not ticker:
            continue
        if tickers is not None and ticker not in tickers:
            print(f"  '{ticker}' is not in the S&P 500 dataset.")
            continue
        buy = read_positive("  Buy price: ", float)
        qty = read_positive("  Shares: ", int)
        if ticker in portfolio:  # merge into weighted-average cost
            old = portfolio[ticker]
            total = old["shares"] + qty
            old["buy_price"] = (old["buy_price"] * old["shares"] + buy * qty) / total
            old["shares"] = total
        else:
            portfolio[ticker] = {
                "name": tickers.get(ticker, "") if tickers else "",
                "buy_price": buy,
                "shares": qty,
                "current_price": get_price(ticker),
            }
    return portfolio


def analyse(portfolio):
    rows = []
    for t, p in portfolio.items():
        invested = p["buy_price"] * p["shares"]
        current = p["current_price"] * p["shares"]
        pct = (current - invested) / invested * 100
        rows.append({"Ticker": t, "Company": p["name"], "Shares": p["shares"],
                     "Buy Price": round(p["buy_price"], 2),
                     "Current Price": round(p["current_price"], 2),
                     "Invested": round(invested, 2),
                     "Current Value": round(current, 2),
                     "Gain/Loss %": round(pct, 2)})
    return rows


def print_report(rows):
    print("\n" + "=" * 80)
    print(f"{'Ticker':<8}{'Shares':>7}{'Buy':>10}{'Now':>10}"
          f"{'Invested':>13}{'Value':>13}{'Gain/Loss':>12}")
    print("-" * 80)
    for r in rows:
        print(f"{r['Ticker']:<8}{r['Shares']:>7}{r['Buy Price']:>10.2f}"
              f"{r['Current Price']:>10.2f}{r['Invested']:>13,.2f}"
              f"{r['Current Value']:>13,.2f}{r['Gain/Loss %']:>11.2f}%")
    invested = sum(r["Invested"] for r in rows)
    value = sum(r["Current Value"] for r in rows)
    pct = (value - invested) / invested * 100 if invested else 0
    print("-" * 80)
    print(f"{'TOTAL':<8}{'':>7}{'':>10}{'':>10}{invested:>13,.2f}{value:>13,.2f}{pct:>11.2f}%")
    print("=" * 80)
    return invested, value, pct


def save_summary(rows, invested, value, pct):
    """Append to CSV so each run is logged."""
    new_file = not os.path.exists(SUMMARY_FILE)
    fields = ["Timestamp"] + list(rows[0].keys())
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SUMMARY_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow({"Timestamp": stamp, **r})
        w.writerow({"Timestamp": stamp, "Ticker": "TOTAL", "Invested": round(invested, 2),
                    "Current Value": round(value, 2), "Gain/Loss %": round(pct, 2)})
    print(f"Summary saved to {SUMMARY_FILE}")


def main():
    tickers = load_tickers(TICKER_FILE)
    portfolio = collect_portfolio(tickers)
    if not portfolio:
        print("No holdings entered.")
        return
    rows = analyse(portfolio)
    invested, value, pct = print_report(rows)
    save_summary(rows, invested, value, pct)


if __name__ == "__main__":
    main()
