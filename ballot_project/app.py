import sqlite3
import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "sponsor_demo_secret"

# 1. DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect('ballot_box.db')
    c = conn.cursor()
    
    # Table 1: THE REGISTRY (Pre-authorized NINs)
    c.execute('''CREATE TABLE IF NOT EXISTS registry 
                 (nin TEXT PRIMARY KEY)''')
    
    # Table 2: VOTER HISTORY (To prevent double voting)
    c.execute('''CREATE TABLE IF NOT EXISTS voters 
                 (voter_hash TEXT PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Table 3: TALLYING RESULTS
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (candidate TEXT PRIMARY KEY, votes INTEGER DEFAULT 0)''')
    
    # --- PRE-LOADING DATA FOR YOUR DEMO ---
    
    # 1. Add some "Official" NINs to the registry
    # In a real system, this would be synced with the National ID database
    official_nins = [('NIN-123456789',), ('NIN-987654321',), ('NIN-555666777',)]
    c.executemany('INSERT OR IGNORE INTO registry VALUES (?)', official_nins)
    
    # 2. Pre-loading Candidates
    candidates = [('Candidate Alpha', 0), ('Candidate Beta', 0), ('Candidate Gamma', 0)]
    c.executemany('INSERT OR IGNORE INTO results VALUES (?, ?)', candidates)
    
    conn.commit()
    conn.close()

init_db()

# 2. ROUTES
@app.route('/')
def index():
    conn = sqlite3.connect('ballot_box.db')
    c = conn.cursor()
    c.execute('SELECT candidate FROM results')
    candidates = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', candidates=candidates)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id').strip() # Get the NIN entered
    choice = request.form.get('candidate')

    if not voter_id or not choice:
        flash("System Error: All fields required.", "error")
        return redirect(url_for('index'))

    conn = sqlite3.connect('ballot_box.db')
    c = conn.cursor()

    # --- STEP 1: AUTHENTICATION (Check if NIN exists in Registry) ---
    c.execute('SELECT * FROM registry WHERE nin = ?', (voter_id,))
    if not c.fetchone():
        conn.close()
        flash("Identity Error: This NIN is not registered in the National Database.", "error")
        return redirect(url_for('index'))

    # --- STEP 2: INTEGRITY (Check for Double Voting) ---
    voter_hash = hashlib.sha256(voter_id.encode()).hexdigest()
    
    try:
        # Attempt to mark this person as having voted
        c.execute('INSERT INTO voters (voter_hash) VALUES (?)', (voter_hash,))
        
        # --- STEP 3: TALLY (Update the results) ---
        c.execute('UPDATE results SET votes = votes + 1 WHERE candidate = ?', (choice,))
        conn.commit()
        flash(f"Authenticity Verified! Vote cast for {choice}.", "success")
    except sqlite3.IntegrityError:
        flash("Security Alert: This NIN has already cast a ballot.", "warning")
    finally:
        conn.close()

    return redirect(url_for('results_page'))

@app.route('/results')
def results_page():
    conn = sqlite3.connect('ballot_box.db')
    c = conn.cursor()
    c.execute('SELECT * FROM results')
    data = dict(c.fetchall())
    conn.close()
    return render_template('results.html', results=data)

    if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=10000)
