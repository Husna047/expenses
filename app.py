from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db():
    return sqlite3.connect(os.path.join(BASE_DIR, 'expenses.db'))

# --- Register ---
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error_message = "⚠️ Username already taken. Please choose another."
            return render_template('register.html', error=error_message)
    return render_template('register.html')

# --- Login ---
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="⚠️ Invalid credentials")
    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for('logout'))
    user_id = row[0]

    c.execute("SELECT id, amount, category, description, date FROM expenses WHERE user_id=? ORDER BY date DESC", (user_id,))
    expenses = c.fetchall()
    conn.close()

    total = sum([row[1] for row in expenses]) if expenses else 0
    return render_template('index.html', expenses=expenses, total=total, user=session['user'])

# --- Add Expense ---
@app.route('/add', methods=['GET','POST'])
def add_expense():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        date = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
        row = c.fetchone()
        if not row:
            conn.close()
            return redirect(url_for('logout'))
        user_id = row[0]

        c.execute("INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?,?,?,?,?)",
                  (user_id, amount, category, description, date))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_expense.html')

# --- Edit Expense ---
@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit_expense(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for('logout'))
    user_id = row[0]

    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        date = request.form['date']

        c.execute("""UPDATE expenses 
                     SET amount=?, category=?, description=?, date=? 
                     WHERE id=? AND user_id=?""",
                  (amount, category, description, date, id, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT id, amount, category, description, date FROM expenses WHERE id=? AND user_id=?", (id, user_id))
    expense = c.fetchone()
    conn.close()
    if not expense:
        return redirect(url_for('index'))

    return render_template('edit_expense.html', expense=expense)

# --- Delete Expense ---
@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for('logout'))
    user_id = row[0]

    c.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- Chart ---
@app.route('/chart')
def chart():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for('logout'))
    user_id = row[0]

    # Group expenses by category
    c.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category", (user_id,))
    data = c.fetchall()
    conn.close()

    labels = [d[0] for d in data]
    values = [d[1] for d in data]

    return render_template('chart.html', user=session['user'], labels=labels, values=values)

if __name__ == "__main__":
    app.run(debug=True)
