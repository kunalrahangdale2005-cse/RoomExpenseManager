from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime
import random
import os

app = Flask(__name__)
app.secret_key = "secretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- USER MODEL ----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    person_name = db.Column(db.String(100), nullable=False)

# ---------------- EXPENSE MODEL ----------------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    person = db.Column(db.String(100))
    item = db.Column(db.String(100))
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)

roommates = [
    "Kunal Rahangdale",
    "Himanshu Rahangdale",
    "Ashish Jaitwar"
]

# ---------------- LOGIN MANAGER ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        person_name = request.form["person_name"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            password=hashed_password,
            person_name=person_name
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration Successful")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid Username or Password")

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------------- HOME ----------------
@app.route("/")
@login_required
def index():
    quotes = [
        "Small expenses become big savings when shared fairly.",
        "Track every rupee, build every dream.",
        "Saving together is growing together.",
        "Shared expenses create stronger friendships.",
        "Transparency builds trust.",
        "Spend wisely, live happily.",
        "Every rupee has a purpose.",
        "Budget today for a better tomorrow.",
        "Good roommates share expenses clearly.",
        "Financial discipline creates freedom."
    ]

    current_date = datetime.now().strftime("%d %B %Y")
    current_day = datetime.now().strftime("%A")
    quote = random.choice(quotes)

    expenses = Expense.query.order_by(Expense.id.desc()).all()

    total = sum(e.amount for e in expenses)
    share = total / len(roommates) if total > 0 else 0

    person_totals = {}
    for e in expenses:
        person_totals[e.person] = person_totals.get(e.person, 0) + e.amount

    balances = {}
    for person in roommates:
        balances[person] = person_totals.get(person, 0) - share

    settlements = []
    receivers = []
    payers = []

    for person, balance in balances.items():
        if balance > 0:
            receivers.append([person, balance])
        elif balance < 0:
            payers.append([person, abs(balance)])

    for payer, pay_amount in payers:
        for receiver in receivers:
            if pay_amount <= 0:
                break

            receiver_name = receiver[0]
            receiver_amount = receiver[1]

            amount = min(pay_amount, receiver_amount)

            settlements.append(
                f"{payer} pays {receiver_name} ₹{round(amount, 2)}"
            )

            pay_amount -= amount
            receiver[1] -= amount

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        share=share,
        balances=balances,
        person_totals=person_totals,
        settlements=settlements,
        current_date=current_date,
        current_day=current_day,
        quote=quote
    )

# ---------------- ADD EXPENSE ----------------
@app.route("/add", methods=["POST"])
@login_required
def add_expense():
    item = request.form["item"]
    category = request.form["category"]
    amount = float(request.form["amount"])

    expense = Expense(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        person=current_user.person_name,
        item=item,
        category=category,
        amount=amount
    )

    db.session.add(expense)
    db.session.commit()

    return redirect(url_for("index"))

# ---------------- DOWNLOAD EXCEL ----------------
@app.route("/download_excel")
@login_required
def download_excel():
    expenses = Expense.query.all()

    df = pd.DataFrame([{
        "Date": e.date,
        "Person": e.person,
        "Item": e.item,
        "Category": e.category,
        "Amount": e.amount
    } for e in expenses])

    file_name = "expenses.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Expenses", index=False)

        total = sum(e.amount for e in expenses)
        share = total / len(roommates) if total > 0 else 0

        person_totals = {}
        for e in expenses:
            person_totals[e.person] = person_totals.get(e.person, 0) + e.amount

        balances = {}
        for person in roommates:
            balances[person] = person_totals.get(person, 0) - share

        summary = pd.DataFrame({
            "Person": list(balances.keys()),
            "Balance": list(balances.values())
        })

        summary.to_excel(writer, sheet_name="Summary", index=False)

    return send_file(file_name, as_attachment=True)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
