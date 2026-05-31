from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = 'chiave_segreta_super_sicura_per_il_prof'

ts = URLSafeTimedSerializer(app.secret_key)

# ==========================================
# CONFIGURAZIONE OAUTH 2.0 (GOOGLE LOGIN)
# ==========================================
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='413339596512-evho3j40c9iss0uoka9me5656c6tlpfv.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ==========================================
# CONFIGURAZIONE DATABASE SUPABASE
# ==========================================
SUPABASE_URL = "https://veaqmkhmbdwjfcjqtpyf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZlYXFta2htYmR3amZjanF0cHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxMjMyNjQsImV4cCI6MjA5NTY5OTI2NH0.lOQrR5G_hY2NEtd-somLLZq4X2PtovXrvt8BFIav2r8"

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
# ACCESSO TRAMITE GOOGLE (SSO)
# ==========================================
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
    except Exception as e:
        return redirect(url_for('auth'))
        
    email = user_info.get('email')
    nome_completo = user_info.get('name')
    
    risposta = supabase.table('utenti').select('*').eq('email', email).execute()
    
    if len(risposta.data) > 0:
        utente_trovato = risposta.data[0]
        session['id_utente'] = utente_trovato['id_utente']
        session['utente_loggato'] = utente_trovato['nome_completo']
        
        if utente_trovato.get('piano_abbonamento') != 'gratuito':
            session['ha_pagato'] = True
            return redirect(url_for('dashboard'))
        else:
            session['ha_pagato'] = False
            return redirect(url_for('checkout'))
    else:
        nuovo_utente = {
            'nome_completo': nome_completo,
            'email': email,
            'password_hash': 'GOOGLE_SSO_NO_PASSWORD',
            'metodo_accesso': 'google',
            'piano_abbonamento': 'gratuito'
        }
        
        inserimento = supabase.table('utenti').insert(nuovo_utente).execute()
        
        session['id_utente'] = inserimento.data[0]['id_utente']
        session['utente_loggato'] = nome_completo
        session['ha_pagato'] = False
        
        return redirect(url_for('checkout'))


# ==========================================
# GESTIONE RESET PASSWORD
# ==========================================
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        risposta = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if len(risposta.data) == 0:
            return render_template('reset_password.html', step='request', error="Nessun account associato a questa email.")
        
        token = ts.dumps(email, salt='recover-key')
        return redirect(url_for('reset_with_token', token=token))
        
    return render_template('reset_password.html', step='request')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = ts.loads(token, salt='recover-key', max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        return render_template('reset_password.html', step='error', error="Il link di ripristino è scaduto o non è valido.")
        
    if request.method == 'POST':
        nuova_password = request.form.get('password')
        conferma_password = request.form.get('confirm_password')
        
        if nuova_password != conferma_password:
            return render_template('reset_password.html', step='change', token=token, error="Le password inserite non coincidono.")
        
        password_criptata = generate_password_hash(nuova_password)
        supabase.table('utenti').update({'password_hash': password_criptata}).eq('email', email).execute()
        
        return render_template('reset_password.html', step='success')
        
    return render_template('reset_password.html', step='change', token=token)


# ==========================================
# ACCESSO E REGISTRAZIONE STANDARD
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
            
            if utente_trovato.get('metodo_accesso') == 'google' and hash_salvato == 'GOOGLE_SSO_NO_PASSWORD':
                return render_template('auth.html', error="Hai creato questo account tramite Google. Usa il pulsante 'Accedi con Google'.")
            
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
# PAGAMENTO / CHECKOUT (INTEGRATO PAYPAL)
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
        
        # CHICCA: Se l'utente ha pagato tramite i bottoni reali, impostiamo il flag identificativo
        ultime_cifre = 'PAYPAL'
        
        # Gestione codici promozionali speciali
        if codice_inserito:
            controllo_promo = supabase.table('codici_promozionali').select('*').eq('codice', codice_inserito).execute()
            if len(controllo_promo.data) > 0:
                dati_codice = controllo_promo.data[0]
                piano_assegnato = dati_codice['tipo_piano']
                giorni_validita = dati_codice['giorni_validita']
                importo_pagato = 0.0
                ultime_cifre = 'VIP0'
                
        # Calcolo dell'importo se non è stato usato un codice sconto totale
        if importo_pagato == 0.0 and ultime_cifre != 'VIP0':
            if piano_scelto == 'starter': importo_pagato = 19.00
            elif piano_scelto == 'pro': importo_pagato = 49.00
            elif piano_scelto == 'elite': importo_pagato = 99.00
            
        data_scadenza = (datetime.now() + timedelta(days=giorni_validita)).isoformat()
        
        # Scrittura dei dati tracciati sul Database Cloud
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