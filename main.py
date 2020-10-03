import sqlite3
from json import load
from flask import Flask, redirect, render_template, request, url_for, send_from_directory
from sys import exit
from time import strftime, strptime


class Config():
    def __init__(self, filename):
        try:
            with open(filename, 'r') as f:
                config = load(f)

            self.person_a       = config['person_a']
            self.person_b       = config['person_b']
            self.currency_long  = config['currency_long']
            self.currency_short = config['currency_short']
            self.database_name  = config['database_name']
        except:
            raise Exception(f"Failed to read the file {filename}")

def connect_to_db(db_name="transactions"):
    """Create a table if it does not exist, and return a conn object"""

    connection = sqlite3.connect(db_name + ".db")
    connection.execute('''CREATE TABLE IF NOT EXISTS transactions
            (id integer PRIMARY KEY,
            date text NOT NULl,
            amount integer,
            delta_a integer,
            delta_b integer,
            description text)''')
    return connection

def log_expense(conn, data):
    """Logs an added expense"""

    sql = '''INSERT INTO 
            transactions(date, amount, delta_a, delta_b, description)
            VALUES (?, ?, ?, ?, ?)'''
    
    cur = conn.cursor()
    cur.execute(sql, (data["date"],
                      - data["amount"],
                      data["delta_a"],
                      data["delta_b"],
                      data["description"]))
    conn.commit()

def log_repayment(conn, data):
    """Logs a repayment to the db"""

    sql = """INSERT INTO 
            transactions(date, amount, delta_a, delta_b, description)
            VALUES (?, ?, ?, ?, ?)"""
    
    cur = conn.cursor()
    cur.execute(sql, (data["date"],
                      data["amount"],
                      data["delta_a"],
                      data["delta_b"],
                      data["description"]))
    conn.commit()

def who_is_in_debt(conn):
    """Returns a tuple of who is in debt and by how much"""
    cur = conn.cursor()
    cur.execute("SELECT delta_a, delta_b FROM transactions")
    rows = cur.fetchall()
    a_balance = 0
    for row in rows:
        a_balance += row[0]
        a_balance -= row[1]
    # if person a's balace is less than
    # 0, they are in debt.
    if a_balance < 0:
        return ('a', abs(a_balance))

    # ...otherwise person b is in debt
    return ('b', abs(a_balance))

def total_expenses(conn, year=strftime("%Y"), month=strftime("%m")):
    """Returns the total expenses for a given year and month"""

    cur = conn.cursor()
    cur.execute(f"""SELECT amount FROM transactions
                WHERE amount < 0
                AND strftime('%m', date) = '{month}'
                AND strftime('%Y', date) = '{year}'""")

    rows = cur.fetchall()
    return abs(sum(map(lambda r: r[0], rows)))


def all_months_with_expenses(conn):
    """Provides a list of all months containing expenses"""
    q = """SELECT DISTINCT
            strftime('%m', date) as Month,
            strftime('%Y', date) as Year 
            FROM transactions 
            WHERE amount < 0
            ORDER BY date(date) DESC, id DESC"""
    cur = conn.cursor()
    cur.execute(q)
    return (cur.fetchall())

def get_transactions(conn, limit=True, n=5):
    """Get a list of transactions"""

    cur = conn.cursor()

    q = "SELECT * FROM transactions ORDER BY date(date) DESC, id DESC"
    if limit:
        q += f" Limit {n}"

    cur.execute(q)
    rows = cur.fetchall()
    
    def convert_row(row):
        """Convert a row to a dict"""

        date = strptime(row[1], "%Y-%m-%d") 

        data = {}
        data['id']        = row[0]
        data['date']      = strftime("%b %d %Y", date)
        data['amount']    = row[2]
        data['delta_a']   = row[3]
        data['delta_b']   = row[4]
        data['comments']  = row[5]
        return data

    return list(map(convert_row, rows))


app = Flask(__name__)
config = Config("configuration.json")


@app.route('/')
def home():
    conn = connect_to_db(config.database_name)
    #print(get_transactions(conn))
    return render_template('home.html',
                            config=config,
                            currently_in_debt=who_is_in_debt(conn),
                            total_expenses=total_expenses(conn),
                            transactions=get_transactions(conn))


@app.route('/log-transaction')
def log_transaction():
    return render_template('add.html', config=config)


@app.route('/all-transactions')
def all_transactions():
    conn = connect_to_db(config.database_name)
    return render_template('allTransactions.html',
                            config=config,
                            transactions=get_transactions(conn, limit=False))


@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    conn = connect_to_db(config.database_name)
    if request.method == 'POST':
        delta_a = 0
        delta_b = 0

        data = request.form.to_dict()
        amount = int(data['amount'])
        debt_type = data['debt']

        if debt_type == 'specify':
            try:
                specified_a = int(data['specifiedPersonA'])
            except:
                specified_a = 0
            
            try:
                specified_b = int(data['specifiedPersonB'])
            except:
                specified_b = 0
            
            delta_a -= specified_a
            delta_b -= specified_b

        elif debt_type == 'personA':
            delta_a -= amount // 2
        else:
            delta_b -= amount // 2

        log_expense(conn, { "amount":amount,
                            "delta_a": delta_a,
                            "delta_b": delta_b,
                            "date": data['date'],
                            "description": data['comments']})

    return redirect(url_for('home'))

@app.route('/add-repayment', methods=['GET', 'POST'])
def add_repayment():
    conn = connect_to_db(config.database_name)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        print(data)
        amount = int(data['amount'])
        delta_a = 0
        delta_b = 0
        if data["payed"] == "payedPersonA":
            delta_a = amount
        else:
            delta_b = amount
        
    log_repayment(conn, {   "amount": amount,
                            "delta_a": delta_a,
                            "delta_b": delta_b,
                            "date": data["date"],
                            "description": data["comments"]})

    return redirect(url_for('home'))

@app.route('/monthly-expenses')
def monthly_expenses():
    conn = connect_to_db(config.database_name)
    expense_cards = []
    expenses_each_month = []
    for i in all_months_with_expenses(conn):
        month = i[0]
        year  = i[1]

        date = strptime(f"{year} {month}", "%Y %m") 
        formated_date = strftime("%b %Y", date)

        expenses = total_expenses(conn, year=year, month=month)
        expenses_each_month.append(expenses)

        expense_cards.append({
            "date": formated_date,
            "expenses": expenses
        })
    
    avg_expenses = sum(expenses_each_month) // len(expenses_each_month) 

    return render_template('monthlyExpenses.html',
                            config=config,
                            avg_expenses=avg_expenses,
                            expense_cards=expense_cards)

@app.route('/remove/<id>')
def remove(id):
    try:
        clean_id = int(id)
    except:
        # todo add error message
        return redirect(url_for('home')) 
    
    conn = connect_to_db(config.database_name)
    cur = conn.cursor()
    q = f"DELETE FROM transactions WHERE id = {clean_id}"
    cur.execute(q)
    conn.commit()

    return redirect(url_for('home')) 