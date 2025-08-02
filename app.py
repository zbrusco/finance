import os

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from models import create_db, ensure_table


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
DATABASE_NAME = "finance.db"
if not os.path.exists(f"./{DATABASE_NAME}"):
    created_db = create_db(DATABASE_NAME)

ensure_table(DATABASE_NAME)
db = SQL(f"sqlite:///{DATABASE_NAME}")


def get_user_cash(n):
    cash = db.execute("SELECT cash FROM users WHERE id = ?", n)
    return int(cash[0]["cash"])


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Update current holdings
    holdings = db.execute(
        "SELECT * FROM holdings WHERE user_id = ? GROUP BY symbol", session["user_id"]
    )

    # Updating the pricing of each symbol
    for holding in holdings:
        stock = lookup(holding["symbol"])
        present_value = holding["shares"] * stock["price"]
        db.execute(
            "UPDATE holdings SET cur_price = ?, present_value = ? WHERE user_id = ? AND symbol = ?",
            stock["price"],
            present_value,
            session["user_id"],
            stock["symbol"],
        )

    # User's current holdings
    shares = db.execute(
        "SELECT * FROM holdings WHERE user_id = ? GROUP BY symbol", session["user_id"]
    )

    # Getting total invested in shares by user
    shares_total = 0
    for share in shares:
        shares_total += share["present_value"]

    # Getting cash balance from user
    cash = get_user_cash(session["user_id"])

    # Getting total balance from user
    total = cash + shares_total

    return render_template("index.html", shares=shares, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # If user submits the form
    if request.method == "POST":

        # Checks if the user input is a valid number
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("Please enter a valid amount of shares", 400)

        # if shares is not a positive number
        if shares <= 0:
            return apology("Please enter a valid amount of shares", 400)

        # If user tries to search without a value
        elif not request.form.get("symbol"):
            return apology("Please enter a stock symbol", 400)

        # If user uses an invalid symbol
        elif lookup(request.form.get("symbol")) == None:
            return apology(
                "The stock symbol you entered is invalid. Please try again.", 400
            )

        # If symbol is valid
        else:
            # Getting stock data from API
            stock = lookup(request.form.get("symbol"))

            # Getting cash balance from user
            cash = get_user_cash(session["user_id"])
            purchase = stock["price"] * shares
            print("Total user cash: ", cash)
            print("Total purchase: ", purchase)

            # Check if user has enough money
            if cash >= purchase:
                cash -= purchase

                db.execute(
                    "UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"]
                )
                db.execute(
                    "INSERT INTO operations (user_id, symbol, shares, price, total, timestamp, type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    session["user_id"],
                    stock["symbol"],
                    shares,
                    stock["price"],
                    purchase,
                    datetime.now(),
                    "BUY",
                )

                flash(f"{shares} shares of {stock["symbol"]} bought successfully!")
                # Query the holdings table for a given stock
                q_holdings = db.execute(
                    "SELECT * FROM holdings WHERE symbol = ? AND user_id = ?",
                    stock["symbol"],
                    session["user_id"],
                )

                # If user has that stock in his holdings
                if q_holdings:
                    # Update the amount of shares
                    total_shares = q_holdings[0]["shares"] + shares
                    cost_basis = q_holdings[0]["cost_basis"] + purchase

                    # calculate the new average price for that stock
                    average = (
                        q_holdings[0]["avg_price"] * q_holdings[0]["shares"] + purchase
                    ) / total_shares
                    db.execute(
                        "UPDATE holdings SET shares = ?, avg_price = ?, cost_basis = ? WHERE user_id = ?",
                        total_shares,
                        average,
                        cost_basis,
                        session["user_id"],
                    )
                    return redirect("/")
                else:
                    average = purchase / shares
                    # add the stock to the user's holdings
                    db.execute(
                        "INSERT INTO holdings (user_id, symbol, shares, avg_price, cur_price, cost_basis) VALUES (?, ?, ?, ?, ?, ?)",
                        session["user_id"],
                        stock["symbol"],
                        shares,
                        average,
                        stock["price"],
                        purchase,
                    )
                    return redirect("/")

            else:
                flash(
                    f"You don't have enough money to buy {shares} shares of {stock["symbol"]}."
                )
                return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    shares = db.execute(
        "SELECT * FROM operations WHERE user_id = ? ORDER BY timestamp DESC",
        session["user_id"],
    )
    return render_template("history.html", shares=shares)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # If user submits the form
    if request.method == "POST":

        # If user tries to search without a value
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol", 400)

        # If user uses an invalid symbol
        elif lookup(request.form.get("symbol")) == None:
            return apology("The stock symbol you entered is invalid", 400)

        # If symbol is valid
        else:
            symbol = lookup(request.form.get("symbol"))
            return render_template("quoted.html", symbol=symbol)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure both password matches
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # Query database for username
        elif db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        ):
            return apology("username already exists", 400)

        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))

        # Insert username and password in the db
        user_id = db.execute(
            "INSERT into users (username, hash) VALUES (?, ?)", username, password
        )

        # Remember which user has logged in
        session["user_id"] = user_id

        # Redirect user to home page
        return redirect("/")

    # User clicked on the register button (or via url)
    else:
        # render the register page instead
        return render_template("register.html")


@app.route("/balance", methods=["GET", "POST"])
@login_required
def balance():
    """Adjust Balance"""
    # Get the user cash
    balance = get_user_cash(session["user_id"])

    if request.method == "POST":
        # Check if the amount is valid
        try:
            amount = int(request.form.get("balance"))
        except ValueError:
            return apology("please enter a valid cash amount", 400)

        if amount <= 0:
            return apology("please enter a valid amount of money", 400)

        # If the user would like to make a deposit
        if request.form.get("action") == "deposit":
            balance += amount
            flash(f"${amount} sucessfully deposited to your account!")
        # If the user would like to make a withdrawal
        else:
            if amount > balance:
                return apology("please enter a valid amount to withdraw", 400)
            else:
                balance -= amount
                flash(f"${amount} successfully withdrawn from your account!")

        # Updating the database
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"]
        )
        return redirect("/balance")
    else:
        return render_template("balance.html", balance=balance)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        # If user chooses an invalid number
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("please enter a valid amount of shares", 400)

        if shares <= 0:
            return apology("please enter a positive amount of shares", 400)

        # Stores the user stocks in a dictionary
        stocks = db.execute(
            "SELECT SUM(shares) as total_shares, symbol, avg_price FROM holdings WHERE user_id = ? GROUP BY symbol",
            session["user_id"],
        )

        # If user chooses an invalid symbol
        if not any(stock["symbol"] == request.form.get("symbol") for stock in stocks):
            return apology("please select a valid symbol", 400)

        # Checking the amount of shares the user owns
        for i, stock in enumerate(stocks):
            if stock["symbol"] == request.form.get("symbol"):
                owned_shares = stock["total_shares"]
                break

        # If the user chooses more shares than he owns
        if shares > owned_shares:
            return apology(
                f"you do not have that amount of shares of {request.form.get("symbol")}",
                400,
            )

        # Else just complete the sell operation
        else:
            q_stock = lookup(request.form.get("symbol"))
            sell_value = q_stock["price"] * shares

            # Update user cash
            cash = get_user_cash(session["user_id"]) + sell_value
            db.execute(
                "UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"]
            )

            # recalculate number of shares
            updated_shares = owned_shares - shares

            # recalculate cost_basis
            cost_basis = stocks[0]["avg_price"] * updated_shares

            # Update user's holdings
            if updated_shares == 0:
                # delete it from the holdings
                db.execute(
                    "DELETE from holdings WHERE user_id = ? AND symbol = ?",
                    session["user_id"],
                    q_stock["symbol"],
                )
            else:
                db.execute(
                    "UPDATE holdings SET shares = ?, cost_basis = ? WHERE user_id = ? AND symbol = ?",
                    updated_shares,
                    cost_basis,
                    session["user_id"],
                    q_stock["symbol"],
                )

            # Compute the sell operation
            db.execute(
                "INSERT INTO operations (user_id, symbol, shares, price, total, timestamp, type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                session["user_id"],
                q_stock["symbol"],
                shares,
                q_stock["price"],
                sell_value,
                datetime.now(),
                "SELL",
            )

            flash(f"{shares} shares of {q_stock["symbol"]} sold successfully!")
            return redirect("/")

    else:
        shares = db.execute(
            "SELECT symbol FROM holdings WHERE user_id = ? GROUP BY symbol",
            session["user_id"],
        )
        return render_template("sell.html", shares=shares)
