# Finance Portfolio Tracker

A Flask web app that simulates stock trading with real-time pricing data. Users can register, log in, buy and sell stocks, track their portfolio, and view transaction history — all using virtual cash.

## Features

- Register / Login with secure password hashing
- Real-time stock quotes
- Buy and sell shares
- Track current holdings and cash balance
- Transaction history log
- Add or withdraw virtual funds

## Stack

- Python Flask
- SQLite (`cs50` SQL wrapper)
- HTML + Bootstrap
- CS50 stock lookup API

## Setup

1. Clone the repo:

   ```bash
   git clone <your-url>
   cd finance
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   flask run
   ```

4. Visit `http://localhost:5000` in your browser.

## Notes

- The app will create `finance.db` automatically on first run.
- All logic is in `app.py`; database/table creation handled in `models.py`.

---

**This is an educational simulation. No real money or trading involved.**
