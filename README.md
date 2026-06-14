# SecureBid

A secure web-based luxury goods auction platform with real-time bidding, role-based access control, and Stripe-backed checkout.

> ICT2216 Secure Software Development — Lab P1 Group 30

## Tech Stack

- **Backend:** Django 4.2 + Django REST Framework + Django Channels
- **Frontend:** React (Vite)
- **Database:** PostgreSQL (Supabase, TLS on port 5432)
- **Payments:** Stripe (test/demo mode)
- **Real-time:** Django Channels WebSocket for live bid updates

## Setup

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Create a .env file (see required vars below), then:
python manage.py migrate
python manage.py runserver
```

For WebSocket/ASGI support, run with Daphne:

```bash
daphne -b 0.0.0.0 -p 8000 securebid.asgi:application
```

#### Required environment variables (`.env`)

```
SECRET_KEY=your-secret-key
DB_HOST=your-supabase-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-db-password
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=no-reply@securebid.local
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies `/api` and `/ws` to the backend on port 8000.

## Project Structure

- `backend/` — Django project (`securebid`) with apps: `accounts`, `auctions`, `payments`, `core`
- `frontend/` — React (Vite) single-page application
- `.github/workflows/` — CI (tests, SAST, dependency audit) and deploy pipelines
- `backend/nginx/` — Nginx reverse proxy configuration for production

## Demo Mode (Payments)

Checkout runs in Stripe **test mode**. Use test card `4242 4242 4242 4242` with any
future expiry date and any CVC to simulate a successful payment. No real charges occur.
