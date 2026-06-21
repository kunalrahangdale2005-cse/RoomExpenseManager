from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secretkey"   # Needed for login sessions

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db = SQLAlchemy(app)

# ------------------ USER MODEL ------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# ------------------ EXPENSE MODEL ------------------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    person = db.Column(db.String(100))
    item = db.Column(db.String(100))
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)

roommates = ["Kunal Rahangdale", "Himanshu Rahangdale", "Ashish Jaitwar"]

# ------------------ LOGIN MANAGER ------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ ROUTES ------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register"))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    expenses = Expense.query.all()
    total = sum(e.amount for e in expenses)
    share = total / len(roommates) if expenses else 0

    person_totals = {}
    for e in expenses:
        person_totals[e.person] = person_totals.get(e.person, 0) + e.amount

    balances = {p: person_totals.get(p, 0) - share for p in roommates}

    return render_template("index.html", expenses=expenses, total=total, share=share, balances=balances)

@app.route("/add", methods=["POST"])
@login_required
def add_expense():
    person = request.form["person"]
    item = request.form["item"]
    category = request.form["category"]
    amount = float(request.form["amount"])
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_expense = Expense(date=date, person=person, item=item, category=category, amount=amount)
    db.session.add(new_expense)
    db.session.commit()

    return redirect(url_for("index"))

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
    if os.path.exists(file_name):
        os.remove(file_name)

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Expenses", index=False)

        total = sum(e.amount for e in expenses)
        share = total / len(roommates) if expenses else 0
        person_totals = {}
        for e in expenses:
            person_totals[e.person] = person_totals.get(e.person, 0) + e.amount
        balances = {p: person_totals.get(p, 0) - share for p in roommates}

        summary_df = pd.DataFrame({
            "Person": list(balances.keys()),
            "Balance": list(balances.values())
        })
        summary_df.loc[len(summary_df)] = ["Total Expenses", total]
        summary_df.loc[len(summary_df)] = ["Each Person’s Share", share]

        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    return send_file(file_name, as_attachment=True)

# ------------------ MAIN ------------------
if __name__ == "__main__":
    with app.app_context():
        db.drop_all()     # reset old tables
        db.create_all()   # create fresh tables with User + Expense
    app.run(debug=True)
