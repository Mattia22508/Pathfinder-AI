from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
# La chiave segreta serve a Flask per ricordare gli utenti attivi
app.secret_key = 'chiave_segreta_super_sicura_per_il_prof'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/manifesto')
def manifesto():
    return render_template('manifesto.html')

@app.route('/come-funziona')
def come_funziona():
    return render_template('come_funziona.html')

@app.route('/reset-password')
def reset_password():
    return render_template('reset_password.html')

# 1. ACCESSO: L'utente inserisce i dati e il sito se lo ricorda
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        # Prendiamo il nome dal form
        username = request.form.get('username')
        
        # Salviamo la sessione (il sito ora sa chi sei)
        session['utente_loggato'] = username
        session['ha_pagato'] = False # Non hai ancora pagato!
        
        # Ti manda a pagare
        return redirect(url_for('checkout'))
        
    return render_template('auth.html')

# 2. PAGAMENTO: Il muro prima dell'IA
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Se non sei loggato, fuori di qui!
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
        
    if request.method == 'POST':
        # Hai cliccato PAGA. Aggiorniamo la sessione
        session['ha_pagato'] = True
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html')

# 3. L'INTELLIGENZA ARTIFICIALE (Stile Gemini)
@app.route('/dashboard')
def dashboard():
    # Sicurezza 1: Sei loggato?
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
    
    # Sicurezza 2: Hai pagato?
    if not session.get('ha_pagato'):
        return redirect(url_for('checkout'))
        
    # Tutto ok, benvenuto!
    return render_template('dashboard.html', username=session['utente_loggato'])

# 4. DISCONNETTI: Cancella la memoria
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)