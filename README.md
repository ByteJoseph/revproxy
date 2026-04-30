# Reverse Proxy Dashboard

This app helps you connect friendly route names (like `/service1`) to real backend services (like `https://api.example.com`) from one simple dashboard.

## What you can do

- Add services from a web dashboard
- Set a route prefix for each service
- Forward requests automatically to the right backend
- Protect dashboard access with a password

## Example

If you save:

- Route Prefix: `/service1`
- Target URL: `https://api.example.com`

Then this request:

- `http://127.0.0.1:5000/service1/users?id=1`

Will be sent to:

- `https://api.example.com/users?id=1`

## Quick Start

1. Install Python packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Create your config file:

   - Copy `.env.example` to `.env`

3. Set a dashboard password (recommended: hashed):

   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
   ```

   Put the output into `.env` as `DASHBOARD_PASSWORD_HASH`.

4. Set a secure session key in `.env`:

   - `FLASK_SECRET_KEY=your-long-random-secret`

5. Run the app:

   ```bash
   python app.py
   ```

6. Open the dashboard:

   - [http://127.0.0.1:5000/dashboard/login](http://127.0.0.1:5000/dashboard/login)

## Dashboard actions

- **Create** a new service mapping
- **Update** existing mappings
- **Delete** mappings you no longer need

## Security notes

- Dashboard access requires a password from `.env`
- `.env` is ignored by git, so secrets are not committed
- Hashed password (`DASHBOARD_PASSWORD_HASH`) is safer than plain text
