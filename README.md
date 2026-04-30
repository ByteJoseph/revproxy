# Flask Reverse Proxy 

This project provides:

- A dashboard to register proxy services dynamically.
- SQLite + SQLAlchemy storage for service definitions.
- Dynamic reverse proxy forwarding based on route prefixes.

## Service Mapping Example

- DB entry: `/service1 -> https://api.example.com`
- Incoming request: `/service1/users?id=1`
- Forwarded request: `https://api.example.com/users?id=1`

## Run Locally

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file from `.env.example`.

4. Configure dashboard auth in `.env` (password is not stored in source code):

   - Preferred (hashed password):

   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
   ```

   Put the generated value in `DASHBOARD_PASSWORD_HASH` inside `.env`.

   - Optional fallback (plain text in `.env`): set `DASHBOARD_PASSWORD`.

   Also set a strong Flask session secret in `.env`:

   - `FLASK_SECRET_KEY`

5. Start the app:

   ```bash
   python app.py
   ```

6. Open dashboard:

   - [http://127.0.0.1:5000/dashboard/login](http://127.0.0.1:5000/dashboard/login)

## Notes

- Hop-by-hop headers are filtered for both request and response.
- The proxy keeps HTTP method, query string, headers (minus hop-by-hop), and request body.
- Longest route-prefix match is used if multiple prefixes could match.
