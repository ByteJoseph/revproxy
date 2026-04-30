from __future__ import annotations

import os
from functools import wraps
from urllib.parse import urljoin

import requests
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///services.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me-in-env")

db = SQLAlchemy(app)

ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
DASHBOARD_AUTH_SESSION_KEY = "dashboard_authenticated"


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    base_url = db.Column(db.String(500), nullable=False)
    route_prefix = db.Column(db.String(200), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Service {self.name} {self.route_prefix} -> {self.base_url}>"


def normalize_prefix(prefix: str) -> str:
    prefix = (prefix or "").strip()
    if not prefix:
        raise ValueError("Route prefix is required")
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if len(prefix) > 1 and prefix.endswith("/"):
        prefix = prefix[:-1]
    return prefix


def get_matching_service(path: str) -> tuple[Service | None, str]:
    services = Service.query.order_by(db.func.length(Service.route_prefix).desc()).all()
    for service in services:
        prefix = service.route_prefix
        if path == prefix:
            return service, ""
        if path.startswith(prefix + "/"):
            return service, path[len(prefix) :]
    return None, ""


def filtered_request_headers() -> dict[str, str]:
    headers = {}
    for key, value in request.headers.items():
        key_lower = key.lower()
        if key_lower in HOP_BY_HOP_HEADERS or key_lower == "host":
            continue
        headers[key] = value
    return headers


def filtered_response_headers(resp: requests.Response) -> list[tuple[str, str]]:
    headers: list[tuple[str, str]] = []
    for key, value in resp.headers.items():
        if key.lower() in HOP_BY_HOP_HEADERS:
            continue
        headers.append((key, value))
    return headers


def get_configured_dashboard_password() -> tuple[str | None, bool]:
    password_hash = os.getenv("DASHBOARD_PASSWORD_HASH")
    if password_hash:
        return password_hash, True

    # Backward-compatible option: plain password from env (still not in source).
    password = os.getenv("DASHBOARD_PASSWORD")
    if password:
        return password, False

    return None, False


def is_dashboard_authenticated() -> bool:
    return bool(session.get(DASHBOARD_AUTH_SESSION_KEY))


def dashboard_login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_dashboard_authenticated():
            return redirect(url_for("dashboard_login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


@app.get("/")
def home():
    return redirect(url_for("dashboard"))


@app.get("/dashboard/login")
def dashboard_login():
    if is_dashboard_authenticated():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.post("/dashboard/login")
def dashboard_login_submit():
    submitted_password = request.form.get("password") or ""
    configured_password, is_hash = get_configured_dashboard_password()

    if not configured_password:
        return Response(
            "Dashboard password is not configured. Set DASHBOARD_PASSWORD_HASH or DASHBOARD_PASSWORD.",
            status=500,
        )

    if is_hash:
        is_valid = check_password_hash(configured_password, submitted_password)
    else:
        is_valid = submitted_password == configured_password

    if not is_valid:
        flash("Invalid password.", "error")
        return redirect(url_for("dashboard_login"))

    session[DASHBOARD_AUTH_SESSION_KEY] = True
    destination = request.args.get("next") or url_for("dashboard")
    return redirect(destination)


@app.post("/dashboard/logout")
def dashboard_logout():
    session.pop(DASHBOARD_AUTH_SESSION_KEY, None)
    flash("You have been logged out.", "success")
    return redirect(url_for("dashboard_login"))


@app.get("/dashboard")
@dashboard_login_required
def dashboard():
    services = Service.query.order_by(Service.route_prefix.asc()).all()
    return render_template("dashboard.html", services=services)


@app.post("/dashboard/services")
@dashboard_login_required
def create_service():
    name = (request.form.get("name") or "").strip()
    base_url = (request.form.get("base_url") or "").strip()
    route_prefix_raw = request.form.get("route_prefix") or ""

    if not name or not base_url or not route_prefix_raw:
        flash("All fields are required.", "error")
        return redirect(url_for("dashboard"))

    try:
        route_prefix = normalize_prefix(route_prefix_raw)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    if route_prefix.startswith("/dashboard"):
        flash("Route prefix cannot start with /dashboard.", "error")
        return redirect(url_for("dashboard"))

    service = Service(name=name, base_url=base_url, route_prefix=route_prefix)
    db.session.add(service)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Could not create service. Ensure route prefix is unique.", "error")
        return redirect(url_for("dashboard"))

    flash("Service created.", "success")
    return redirect(url_for("dashboard"))


@app.post("/dashboard/services/<int:service_id>/update")
@dashboard_login_required
def update_service(service_id: int):
    service = Service.query.get_or_404(service_id)
    name = (request.form.get("name") or "").strip()
    base_url = (request.form.get("base_url") or "").strip()
    route_prefix_raw = request.form.get("route_prefix") or ""

    if not name or not base_url or not route_prefix_raw:
        flash("All fields are required.", "error")
        return redirect(url_for("dashboard"))

    try:
        route_prefix = normalize_prefix(route_prefix_raw)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    if route_prefix.startswith("/dashboard"):
        flash("Route prefix cannot start with /dashboard.", "error")
        return redirect(url_for("dashboard"))

    service.name = name
    service.base_url = base_url
    service.route_prefix = route_prefix

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Could not update service. Ensure route prefix is unique.", "error")
        return redirect(url_for("dashboard"))

    flash("Service updated.", "success")
    return redirect(url_for("dashboard"))


@app.post("/dashboard/services/<int:service_id>/delete")
@dashboard_login_required
def delete_service(service_id: int):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash("Service deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/<path:req_path>", methods=ALL_METHODS)
def reverse_proxy(req_path: str):
    request_path = f"/{req_path}"
    service, suffix = get_matching_service(request_path)

    if service is None:
        return Response("No matching service configured", status=404)

    upstream_base = service.base_url.rstrip("/")
    target_path = suffix if suffix else "/"
    target_url = urljoin(upstream_base + "/", target_path.lstrip("/"))

    if request.query_string:
        target_url = f"{target_url}?{request.query_string.decode('utf-8')}"

    try:
        upstream_response = requests.request(
            method=request.method,
            url=target_url,
            headers=filtered_request_headers(),
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
        )
    except requests.RequestException as exc:
        return Response(f"Upstream request failed: {exc}", status=502)

    return Response(
        upstream_response.content,
        status=upstream_response.status_code,
        headers=filtered_response_headers(upstream_response),
    )


def init_db() -> None:
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
