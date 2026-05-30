from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# La chiave segreta serve a Flask per ricordare gli utenti attivi
app.secret_key = 'chiave_segreta_super_sicura_per_il_prof'

# ==========================================
# CONFIGURAZIONE DATABASE SUPABASE
# ==========================================
SUPABASE_URL = "https://veaqmkhmbdwjfcjqtpyf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlYXFta2htYmR3amZjanF0cHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxMjMyNjQsImV4cCI6MjA5NTY5OTI2NH0.lOQrR5G_hY2NEtd-somLLZq4X2PtovXrvt8BFIav2r8"

# Inizializziamo il client per parlare con il Database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# ==========================================
# 1. ACCESSO E REGISTRAZIONE (Flusso Corretto)
# ==========================================
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Controlliamo se l'utente esiste già nel database tramite l'email
        risposta = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if len(risposta.data) > 0:
            # L'UTENTE ESISTE! (Fase di Login)
            utente_trovato = risposta.data[0]
            hash_salvato = utente_trovato.get('password_hash')
            
            # Controllo ibrido sicuro: gestisce sia password criptate che testo in chiaro
            password_corretta = False
            if hash_salvato:
                if ':' in hash_salvato or '$' in hash_salvato:
                    password_corretta = check_password_hash(hash_salvato, password if password else '')
                else:
                    password_corretta = (hash_salvato == password)
            else:
                password_corretta = True
                
            if not password_corretta:
                return render_template('auth.html', error="Password errata!")
            
            # Salviamo i dati fondamentali in sessione
            session['id_utente'] = utente_trovato['id_utente']
            session['utente_loggato'] = utente_trovato['nome_completo']
            
            # Se ha già un abbonamento attivo va in dashboard, altrimenti va a pagare!
            if utente_trovato.get('piano_abbonamento') != 'gratuito':
                session['ha_pagato'] = True
                return redirect(url_for('dashboard'))
            else:
                session['ha_pagato'] = False
                return redirect(url_for('checkout'))
                
        else:
            # L'UTENTE È NUOVO! (Fase di Registrazione)
            password_criptata = generate_password_hash(password) if password else None
            
            nuovo_utente = {
                'nome_completo': username,
                'email': email,
                'password_hash': password_criptata,
                'metodo_accesso': 'email',
                'piano_abbonamento': 'gratuito'
            }
            
            inserimento = supabase.table('utenti').insert(nuovo_utente).execute()
            
            session['id_utente'] = inserimento.data[0]['id_utente']
            session['utente_loggato'] = username
            session['ha_pagato'] = False
            
            # Spediamo il nuovo utente dritto alla pagina pagamenti
            return redirect(url_for('checkout'))
        
    return render_template('auth.html')

# ==========================================
# 2. PAGAMENTO / CHECKOUT (Ripristinato)
# ==========================================
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Ripristinato il controllo originale flessibile: basta che sia loggato l'utente
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
        
    if request.method == 'POST':
        piano_scelto = request.form.get('piano', 'starter')
        codice_inserito = request.form.get('promo_code', '').strip().upper()
        
        importo_pagato = 0.0
        giorni_validita = 30
        piano_assegnato = piano_scelto
        ultime_cifre = '4242'
        
        if codice_inserito:
            controllo_promo = supabase.table('codici_promozionali').select('*').eq('codice', codice_inserito).execute()
            if len(controllo_promo.data) > 0:
                dati_codice = controllo_promo.data[0]
                piano_assegnato = dati_codice['tipo_piano']
                giorni_validita = dati_codice['giorni_validita']
                importo_pagato = 0.0
                ultime_cifre = 'VIP0'
                
        if importo_pagato == 0.0 and ultime_cifre != 'VIP0':
            if piano_scelto == 'starter': importo_pagato = 19.00
            elif piano_scelto == 'pro': importo_pagato = 49.00
            elif piano_scelto == 'elite': importo_pagato = 99.00
            
        data_scadenza = (datetime.now() + timedelta(days=giorni_validita)).isoformat()
        
        # Salviamo la transazione
        nuova_transazione = {
            'id_utente': session.get('id_utente'),
            'piano_acquistato': piano_assegnato,
            'importo': importo_pagato,
            'ultime_cifre_carta': ultime_cifre
        }
        supabase.table('transazioni').insert(nuova_transazione).execute()
        
        # Aggiorniamo il piano dell'utente
        supabase.table('utenti').update({
            'piano_abbonamento': piano_assegnato,
            'scadenza_abbonamento': data_scadenza
        }).eq('id_utente', session.get('id_utente')).execute()

        # Pagamento sbloccato, andiamo alla dashboard!
        session['ha_pagato'] = True
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html')

# ==========================================
# 3. AREA RISERVATA / DASHBOARD
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
    
    if not session.get('ha_pagato'):
        return redirect(url_for('checkout'))
        
    return render_template('dashboard.html', username=session['utente_loggato'])

# ==========================================
# 4. DISCONNESSIONE
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)