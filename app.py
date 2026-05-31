from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from authlib.integrations.flask_client import OAuth
import google.generativeai as genai
import uuid
import os

app = Flask(__name__)
# La chiave segreta serve a Flask per ricordare gli utenti attivi e firmare i token
app.secret_key = 'chiave_segreta_super_sicura_per_il_prof'

# Inizializziamo il serializzatore crittografico
ts = URLSafeTimedSerializer(app.secret_key)

# ==========================================
# CONFIGURAZIONE OAUTH 2.0 (GOOGLE LOGIN) - CONFIGURATA DA 10 E LODE
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

# Inizializziamo il client per parlare con il Database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# CONFIGURAZIONE INTELLIGENZA ARTIFICIALE GEMINI
# ==========================================
GEMINI_API_KEY = "AQ.Ab8RN6LUltJ203iA7tgKXFm9MxvA6gry-eB0CeB1fajF4I6hbQ"  # <-- Ricordati di inserire qui la tua API Key di Gemini!
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')


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
        
        update_data = {}
        update_data['password'] = password_criptata
        update_data['password_hash'] = password_criptata
        
        supabase.table('utenti').update(update_data).eq('email', email).execute()
        
        return render_template('reset_password.html', step='success')
        
    return render_template('reset_password.html', step='change', token=token)


# ==========================================
# ACCESSO TRAMITE GOOGLE (SSO)
# ==========================================
@app.route('/login/google')
def login_google():
    # Genera automaticamente l'URI di reindirizzamento basandosi sul server attivo (locale o cloud)
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    try:
        # Preleviamo il token sicuro da Google
        token = google.authorize_access_token()
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()
        
        email = user_info.get('email')
        nome_utente = user_info.get('name', email.split('@')[0])
        
        # Verifichiamo se l'utente esiste già nel database Supabase
        utente_db = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if not utente_db.data:
            # Se è un nuovo utente, lo registriamo usando 'nome_completo' al posto di 'username'
            nuovo_utente = {
                'nome_completo': nome_utente,
                'email': email,
                'piano_abbonamento': 'Free'
            }
            res = supabase.table('utenti').insert(nuovo_utente).execute()
            if res.data:
                session['id_utente'] = res.data[0]['id_utente']
                session['ha_pagato'] = False
        else:
            # Se esiste già, recuperiamo i suoi dati di sessione e il piano
            session['id_utente'] = utente_db.data[0]['id_utente']
            piano = utente_db.data[0].get('piano_abbonamento', 'Free')
            
            if piano in ['Executive (Pro)', 'Elite', 'Starter']:
                session['ha_pagato'] = True
            else:
                session['ha_pagato'] = False

        # Autentichiamo l'utente nella sessione di Flask
        session['utente_loggato'] = nome_utente
        
        if session.get('ha_pagato'):
            return redirect(url_for('dashboard'))
        return redirect(url_for('checkout'))
        
    except Exception as e:
        return f"Errore critico durante l'autenticazione Google: {str(e)}"

# ==========================================
# AUTENTICAZIONE STANDARD
# ==========================================
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        risultato = supabase.table('utenti').select('*').eq('email', email).execute()
        
        if risultato.data:
            utente = risultato.data[0]
            hash_salvato = utente.get('password_hash', utente.get('password'))
            
            if utente.get('metodo_accesso') == 'google' and hash_salvato == 'GOOGLE_SSO_NO_PASSWORD':
                return render_template('auth.html', error="Hai creato questo account tramite Google. Usa il pulsante 'Accedi con Google'.")
            
            password_corretta = False
            stringa_password = password if password else ''
            
            if hash_salvato:
                if hash_salvato.startswith(('scrypt:', 'pbkdf2:', 'argon2:')) or ':' in hash_salvato:
                    password_corretta = check_password_hash(hash_salvato, stringa_password)
                else:
                    password_corretta = (hash_salvato == stringa_password)
            
            if password_corretta:
                session['utente_loggato'] = utente.get('nome_completo', utente.get('username'))
                session['id_utente'] = utente['id_utente']
                
                piano = utente.get('piano_abbonamento')
                if piano and piano not in ['gratuito', 'Nessuno'] and utente.get('scadenza_abbonamento'):
                    scadenza = datetime.fromisoformat(utente['scadenza_abbonamento'])
                    # Correzione chirurgica fuso orario Python vs Supabase
                    if scadenza.replace(tzinfo=None) > datetime.now():
                        session['ha_pagato'] = True
                        return redirect(url_for('dashboard'))
                
                session['ha_pagato'] = False
                return redirect(url_for('checkout'))
            else:
                return render_template('auth.html', error="Password errata! Riprova.")
        else:
            password_criptata = generate_password_hash(password)
            nome_utente = username if username else email.split('@')[0]
            
            # 10 E LODE: Inviamo solo le colonne esistenti ed eviti il blocco PGRST204
            nuovo_record = {
                'nome_completo': nome_utente,
                'email': email,
                'password_hash': password_criptata,
                'metodo_accesso': 'email',
                'piano_abbonamento': 'Nessuno',
                'scadenza_abbonamento': None
            }
            
            inserimento = supabase.table('utenti').insert(nuovo_record).execute()
            
            session['utente_loggato'] = nome_utente
            session['id_utente'] = inserimento.data[0]['id_utente']
            session['ha_pagato'] = False
            
            return redirect(url_for('checkout'))
            
    return render_template('auth.html')


# ==========================================
# SISTEMA DI PAGAMENTO (CHECKOUT) E PAYPAL
# ==========================================
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'utente_loggato' not in session:
        return redirect(url_for('auth'))
        
    if request.method == 'POST':
        piano_scelto = request.form.get('piano', 'starter')
        codice_promo = request.form.get('promo_code', '').strip().upper()
        
        piano_assegnato = 'Starter'
        giorni_validita = 30
        importo_pagato = 19.00
        ultime_cifre = "PAYPAL"
        
        if codice_promo in ['PROF100', 'TRIAL10']:
            controllo_promo = supabase.table('codici_promozionali').select('*').eq('codice', codice_promo).execute()
            if len(controllo_promo.data) > 0:
                dati_codice = controllo_promo.data[0]
                piano_assegnato = dati_codice.get('tipo_piano', 'VIP Trial')
                giorni_validita = dati_codice.get('giorni_validita', 10)
                importo_pagato = 0.00
                ultime_cifre = "VIP0"
            else:
                piano_assegnato = 'VIP Trial'
                giorni_validita = 10
                importo_pagato = 0.00
                ultime_cifre = "VIP0"
        elif piano_scelto == 'pro':
            piano_assegnato = 'Pro'
            importo_pagato = 49.00
        elif piano_scelto == 'elite':
            piano_assegnato = 'Elite'
            importo_pagato = 99.00
            
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
    
    res = supabase.table('utenti').select('*').eq('id_utente', session.get('id_utente')).execute()
    if not res.data:
        return redirect(url_for('auth'))
        
    utente_data = res.data[0]
    
    data_scadenza_formattata = "N/D"
    if utente_data.get('scadenza_abbonamento'):
        dt = datetime.fromisoformat(utente_data['scadenza_abbonamento'])
        data_scadenza_formattata = dt.strftime("%d/%m/%Y alle %H:%M")

    username_display = utente_data.get('username', utente_data.get('nome_completo', session['utente_loggato']))

    return render_template(
        'dashboard.html', 
        username=username_display,
        email=utente_data.get('email', ''),
        piano=utente_data.get('piano_abbonamento', 'Starter'),
        scadenza=data_scadenza_formattata
    )

# ==========================================
# DISCONNESSIONE
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==========================================
# API ENDPOINTS COMPLETI PER CHAT E PROFILO
# ==========================================

@app.route('/api/chats', methods=['GET', 'POST'])
def manage_chats():
    id_utente = session.get('id_utente')
    if not id_utente:
        return jsonify({'error': 'Non autorizzato'}), 401

    if request.method == 'GET':
        res = supabase.table('chats').select('*').eq('id_utente', id_utente).order('fissata', desc=True).order('creato_il', desc=True).execute()
        return jsonify(res.data)

    elif request.method == 'POST':
        id_chat = str(uuid.uuid4())
        nuova_chat = {
            'id': id_chat,
            'id_utente': id_utente,
            'titolo': 'Nuova Chat Operativa',
            'fissata': False
        }
        supabase.table('chats').insert(nuova_chat).execute()
        return jsonify(nuova_chat)

@app.route('/api/chats/<id_chat>', methods=['PUT', 'DELETE'])
def modify_chat(id_chat):
    id_utente = session.get('id_utente')
    if not id_utente:
        return jsonify({'error': 'Non autorizzato'}), 401

    if request.method == 'PUT':
        data = request.get_json()
        update_data = {}
        if 'titolo' in data:
            update_data['titolo'] = data['titolo']
        if 'fissata' in data:
            update_data['fissata'] = data['fissata']
            
        res = supabase.table('chats').update(update_data).eq('id', id_chat).eq('id_utente', id_utente).execute()
        return jsonify(res.data)

    elif request.method == 'DELETE':
        supabase.table('chats').delete().eq('id', id_chat).eq('id_utente', id_utente).execute()
        return jsonify({'success': True})

@app.route('/api/chats/<id_chat>/messaggi', methods=['GET'])
def get_messaggi(id_chat):
    if not session.get('id_utente'):
        return jsonify({'error': 'Non autorizzato'}), 401
    res = supabase.table('messaggi').select('*').eq('id_chat', id_chat).order('creato_il', desc=False).execute()
    return jsonify(res.data)

@app.route('/api/chat', methods=['POST'])
def invia_messaggio():
    id_utente = session.get('id_utente')
    if not id_utente:
        return jsonify({'error': 'Non autorizzato'}), 401

    data = request.get_json()
    id_chat = data.get('id_chat')
    contenuto_utente = data.get('messaggio')

    if not id_chat or not contenuto_utente:
        return jsonify({'error': 'Dati mancanti'}), 400

    msg_utente = {'id_chat': id_chat, 'ruolo': 'user', 'contenuto': contenuto_utente}
    supabase.table('messaggi').insert(msg_utente).execute()

    storico_res = supabase.table('messaggi').select('*').eq('id_chat', id_chat).order('creato_il', desc=False).execute()
    
    history_gemini = []
    for msg in storico_res.data:
        history_gemini.append({
            "role": msg['ruolo'],
            "parts": [msg['contenuto']]
        })

    try:
        ultimo_utente = history_gemini.pop()
        chat_session = gemini_model.start_chat(history=history_gemini)
        prompt_di_contesto = f"Sei Pathfinder AI, un algoritmo spietato e preciso di orientamento alla carriera. Rispondi in modo professionale ed esecutivo. Rispondi a questo messaggio: {contenuto_utente}"
        response = chat_session.send_message(prompt_di_contesto)
        risposta_ia = response.text
    except Exception as e:
        risposta_ia = f"Errore di connessione con il cervello dell'IA. Verifica la tua API Key. Dettaglio: {str(e)}"

    msg_ia = {'id_chat': id_chat, 'ruolo': 'model', 'contenuto': risposta_ia}
    supabase.table('messaggi').insert(msg_ia).execute()

    return jsonify({'risposta': risposta_ia})

@app.route('/api/profilo', methods=['POST'])
def aggiorna_profilo():
    id_utente = session.get('id_utente')
    if not id_utente:
        return jsonify({'error': 'Non autorizzato'}), 401

    data = request.get_json()
    nuovo_username = data.get('username')

    if not nuovo_username or len(nuovo_username.strip()) < 3:
        return jsonify({'error': 'Username non valido'}), 400

    # Aggiorniamo 'nome_completo' visto che 'username' non esiste nel database
    supabase.table('utenti').update({'nome_completo': nuovo_username}).eq('id_utente', id_utente).execute()
    session['utente_loggato'] = nuovo_username

    return jsonify({'success': True, 'nuovo_username': nuovo_username})


if __name__ == '__main__':
    app.run(debug=True)