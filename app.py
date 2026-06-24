from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import random

app = Flask(__name__)
app.secret_key = "secretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://roomexpense_db_user:oREPnRZ0v3W76yRfaSJb0G5Gx4xNH02K@dpg-d8tb64jtqb8s73ff0er0-a.virginia-postgres.render.com/roomexpense_db'
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
        user = User(username=username, password=hashed_password, person_name=person_name)
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

    current_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %B %Y")
    current_day = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A")
    quote = random.choice(quotes)

    expenses = Expense.query.order_by(Expense.id.desc()).all()
    total = sum(e.amount for e in expenses)
    share = round(total / len(roommates), 2) if roommates else 0

    # Person Totals
    person_totals = {}
    for e in expenses:
        person_totals[e.person] = person_totals.get(e.person, 0) + e.amount

    # Net Settlement
    balances = {}
    for person in roommates:
        balances[person] = person_totals.get(person, 0) - share

    status_messages = {}
    for person, balance in balances.items():
        if balance > 0:
            status_messages[person] = f"Receive ₹{round(balance,2)} from others"
        elif balance < 0:
            main_receiver = max(balances, key=balances.get) if balances else "No one"
            status_messages[person] = f"Pay {main_receiver} ₹{round(abs(balance),2)}"
        else:
            status_messages[person] = "Settled"

    # ---------------- Final Settlement (structured dicts) ----------------
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
            if amount > 0:
                settlements.append({
                    "payer": payer,
                    "receiver": receiver_name,
                    "amount": round(amount, 2),
                    "remarks": "Remaining amount after all mutual adjustments"
                })
                pay_amount -= amount
                receiver[1] -= amount

    # ---------------- Detailed Expense Split (structured dicts) ----------------
    detailed_settlements = []
    for e in expenses:
        split_amount = round(e.amount / len(roommates), 2)
        split_details = []
        for person in roommates:
            if person != e.person:
                split_details.append(f"{person} → ₹{split_amount}")
        detailed_settlements.append({
            "expense": e.item,
            "paid_by": e.person,
            "amount": round(e.amount, 2),
            "split_details": ", ".join(split_details)
        })

    # ---------------- Settlement Calculation ----------------
    calculation_details = {}
    for person in roommates:
        received_list = []
        paid_list = []
        total_received = 0
        total_paid = 0

        for ds in detailed_settlements:
            for detail in ds["split_details"].split(", "):
                if detail.startswith(person):
                    amount = float(detail.split("₹")[1])
                    paid_list.append(f"{detail} to {ds['paid_by']}")
                    total_paid += amount
                elif ds["paid_by"] == person:
                    amount = float(detail.split("₹")[1])
                    received_list.append(f"{detail} from {ds['expense']}")
                    total_received += amount

        net_amount = round(total_received - total_paid, 2)

        calculation_details[person] = {
            "received_list": received_list,
            "paid_list": paid_list,
            "total_received": round(total_received, 2),
            "total_paid": round(total_paid, 2),
            "net_amount": net_amount
        }

    return render_template(
        "index.html",
        expenses=expenses,
        total=round(total, 2),
        share=round(share, 2),
        balances=balances,
        person_totals=person_totals,
        settlements=settlements,
        detailed_settlements=detailed_settlements,
        current_date=current_date,
        current_day=current_day,
        quote=quote,
        status_messages=status_messages,
        roommates=roommates,
        calculation_details=calculation_details
    )

# ---------------- ADD EXPENSE ----------------
@app.route("/add", methods=["POST"])
@login_required
def add_expense():
    item = request.form["item"]
    category = request.form["category"]
    amount = float(request.form["amount"])

    expense = Expense(
        date=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
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
        # Expenses sheet
        df.to_excel(writer, sheet_name="Expenses", index=False)

        # Summary sheet
        total = sum(e.amount for e in expenses)
        share = round(total / len(roommates), 2) if roommates else 0
