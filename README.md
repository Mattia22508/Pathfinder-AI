
# Pathfinder AI - Piattaforma di Orientamento alla Carriera
![Pathfinder AI Banner](https://img.shields.io/badge/Pathfinder%20AI-10%20e%20Lode-00FFCC?style=for-the-badge&logo=google-gemini&logoColor=white)

Pathfinder AI è un'applicazione web avanzata che sfrutta l'intelligenza artificiale per fornire un orientamento alla carriera spietato, preciso ed esecutivo. L'algoritmo agisce come un mentore digitale, analizzando CV e richieste degli utenti per costruire roadmap professionali, suggerire percorsi formativi e ottimizzare le strategie di inserimento nel mondo del lavoro.

## Funzionalità Principali

* **Cervello IA Integrato:** Connessione diretta ai potentissimi modelli **Google Gemini (3.5 Flash)** tramite il nuovo SDK ufficiale Google GenAI.
* **In-Memory File Processing:** Sistema di upload avanzato che permette agli utenti di allegare il proprio CV (PDF, TXT, DOCX) convertendolo istantaneamente in byte e iniettandolo nella rete neurale di Gemini senza intasare il database o lo storage.
* **Autenticazione Blindata:** * Registrazione classica con hashing crittografico delle password (`Werkzeug Security`).
    * Accesso **Single Sign-On (SSO) con Google** OAuth 2.0.
    * Sistema di Reset Password sicuro con token a scadenza temporizzata via email.
* **Chat Dinamica con Markdown:** Interfaccia utente cyber-punk in tempo reale con gestione delle chat storiche (memorizzate su cloud) e renderizzazione perfetta dell'output dell'IA (grassetto, liste, titoli) grazie all'integrazione di `marked.js`.
* **Gestione Abbonamenti e Checkout:** Sistema di sottoscrizione multi-livello (Starter, Pro, Elite) con supporto a codici promozionali speciali (es. `PROF100`) e pagamenti paypal,carta di credito.
* **Database Serverless:** Salvataggio sicuro in cloud di messaggi, credenziali e dati transazionali tramite **Supabase (PostgreSQL)**.

## Tecnologie Utilizzate

### Backend & AI
* ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) **Python 3.x**
* ![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white) **Flask** (Web Framework)
* ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google%20gemini&logoColor=white) **Google GenAI SDK** (`google-genai`)
* **Authlib** (Per l'integrazione OAuth Google)

### Database & Cloud
* ![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white) **Supabase** (PostgreSQL)

### Frontend
* ![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white) **HTML5** & ![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white) **CSS3**
* ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E) **JavaScript (ES6)**
* **Marked.js** (Parsing dinamico del Markdown)

---

## Istruzioni Essenziali di Esecuzione

Per far girare il progetto in locale sulla tua macchina, segui questi passaggi:

### 1. Clonare la Repository
```bash
git clone [https://github.com/Mattia22508/Pathfinder-AI](https://github.com/Mattia22508/Pathfinder-AI)
cd Pathfinder-AI

2. Creare un Ambiente Virtuale (Consigliato)
Bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

3. Installare le Dipendenze
Assicurati di installare tutte le librerie necessarie:

Bash
pip install flask supabase authlib werkzeug itsdangerous google-genai

4. Configurare le API Key
Prima di avviare il server, assicurati di aver inserito le tue chiavi in app.py o come variabili d'ambiente:

SUPABASE_URL e SUPABASE_KEY (Per la connessione al database)

client_id e client_secret (Per il login di Google)

GEMINI_API_KEY (Per l'intelligenza artificiale)

5. Avviare il Server
Bash
python app.py
L'applicazione sarà disponibile localmente all'indirizzo: http://127.0.0.1:5000

Sito Pubblicato (Live Demo)
L'applicazione è interamente online, configurata e accessibile in produzione.

🔗 pathfinder-ai-omega.vercel.app

(Nota per il Prof: Inserire il codice promozionale PROF100 durante la schermata di checkout simulata per ottenere l'accesso VIP gratuito ed illimitato)
