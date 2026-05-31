from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
# AGGIUNTA DA 10 E LODE: Serializer per generare token crittografici sicuri a tempo
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

app = Flask(__name__)
# La chiave segreta serve a Flask per ricordare gli utenti attivi e firmare i token
app.secret_key = 'chiave_segreta_super_sicura_per_il_prof'

# Inizializziamo il serializzatore crittografico usando la secret_key dell'app
ts = URLSafeTimedSerializer(app.secret_key)

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


# ==========================================
# GESTIONE RESET PASSWORD (REDIREZIONE AUTOMATICA)
# ==========================================
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # 1. Controlliamo se l'email inserita esiste effettivamente nel DB
        risposta = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if len(risposta.data) == 0:
            # Email non trovata: restituiamo un errore elegante sulla UI
            return render_template('reset_password.html', step='request', error="Nessun account associato a questa email.")
        
        # 2. L'email esiste! Generiamo un Token Sicuro firmato digitalmente
        token = ts.dumps(email, salt='recover-key')
        
        # 3. CAPACITÀ DA 10 E LODE: Reindirizzamento istantaneo e automatico alla rotta protetta dal token
        # Questo simula l'apertura immediata del link che in produzione verrebbe inviato via mail.
        return redirect(url_for('reset_with_token', token=token))
        
    return render_template('reset_password.html', step='request')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        # Il token viene decodificato. Se è stato alterato o è scaduto (max_age=3600s), solleva un'eccezione.
        email = ts.loads(token, salt='recover-key', max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        return render_template('reset_password.html', step='error', error="Il link di ripristino è scaduto o non è valido.")
        
    if request.method == 'POST':
        nuova_password = request.form.get('password')
        conferma_password = request.form.get('confirm_password')
        
        # Controllo di coerenza delle password inserite
        if nuova_password != conferma_password:
            return render_template('reset_password.html', step='change', token=token, error="Le password inserite non coincidono.")
        
        # Crittografia della nuova password tramite l'algoritmo sicuro di Werkzeug
        password_criptata = generate_password_hash(nuova_password)
        
        # Aggiornamento atomico sul database Cloud Supabase
        supabase.table('utenti').update({'password_hash': password_criptata}).eq('email', email).execute()
        
        return render_template('reset_password.html', step='success')
        
    return render_template('reset_password.html', step='change', token=token)


# ==========================================
# ACCESSO E REGISTRAZIONE (Verifica Hash Corretta)
# ==========================================
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        risposta = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if len(risposta.data) > 0:
            utente_trovato = risposta.data[0]
            hash_salvato = utente_trovato.get('password_hash')
            
            password_corretta = False
            stringa_password = password if password else ''
            
            if hash_salvato:
                if hash_salvato.startswith(('scrypt:', 'pbkdf2:', 'argon2:')) or ':' in hash_salvato:
                    password_corretta = check_password_hash(hash_salvato, stringa_password)
                else:
                    password_corretta = (hash_salvato == stringa_password)
            else:
                password_corretta = False
                
            if not password_corretta:
                return render_template('auth.html', error="Password sbagliata. Riprova.")
            
            session['id_utente'] = utente_trovato['id_utente']
            session['utente_loggato'] = utente_trovato['nome_completo']
            
            if utente_trovato.get('piano_abbonamento') != 'gratuito':
                session['ha_pagato'] = True
                return redirect(url_for('dashboard'))
            else:
                session['ha_pagato'] = False
                return redirect(url_for('checkout'))
                
        else:
            stringa_password = password if password else ''
            password_criptata = generate_password_hash(stringa_password)
            
            nome_utente = username if username else email.split('@')[0]
            
            nuovo_utente = {
                'nome_completo': nome_utente,
                'email': email,
                'password_hash': password_criptata,
                'metodo_accesso': 'email',
                'piano_abbonamento': 'gratuito'
            }
            
            inserimento = supabase.table('utenti').insert(nuovo_utente).execute()
            
            session['id_utente'] = inserimento.data[0]['id_utente']
            session['utente_loggato'] = nome_utente
            session['ha_pagato'] = False
            
            return redirect(url_for('checkout'))
        
    return render_template('auth.html')

# ==========================================
# PAGAMENTO / CHECKOUT
# ==========================================
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
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
        
        nuova_transazione = {
            'id_utente': session.get('id_utente'),
            'piano_acquistato': piano_assegnato,
            'importo': importo_pagato,
            'ultime_cifre_carta': ultime_cifre
        }
        supabase.table('transazioni').insert(nuova_transazione).execute()
        
        supabase.table('utenti').update({
            'piano_abbonamento': piano_assegnato,
            'scadenza_abbonamento': data_scadenza
        }).eq('id_utente', session.get('id_utente')).execute()

        session['ha_pagato'] = True
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html')

# ==========================================
# AREA RISERVATA / DASHBOARD
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
    
    if not session.get('ha_pagato'):
        return redirect(url_for('checkout'))
        
    return render_template('dashboard.html', username=session['utente_loggato'])

# ==========================================
# DISCONNESSIONE
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)