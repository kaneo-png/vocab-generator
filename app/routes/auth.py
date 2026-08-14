import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.services.rate_limit import login_rate_limiter, RateLimitExceeded
from app.services.mailer import send_verification_email
from app.services.guest import migrate_guest_wordlists


auth_bp = Blueprint("auth", __name__)

TOKEN_TTL_HOURS = 24


def _is_token_expired(expiry) -> bool:
    """検証トークンの有効期限切れを判定する（tz非依存で安全に比較）。"""
    if expiry is None:
        return True
    # SQLiteから読むとnaiveになるため、awareへ揃える
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry < datetime.now(timezone.utc)


def _issue_verification(user) -> None:
    """検証トークンを発行して確認メールを送信する。"""
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_token_expiry = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    db.session.commit()
    send_verification_email(user, token)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or not password:
            flash("メールアドレスとパスワードを入力してください。", "error")
            return render_template("auth/register.html")

        if password != confirm:
            flash("パスワードが一致しません。", "error")
            return render_template("auth/register.html")

        if len(password) < 8:
            flash("パスワードは8文字以上にしてください。", "error")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("このメールアドレスは既に登録されています。", "error")
            return render_template("auth/register.html")

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        migrated = migrate_guest_wordlists(user)

        # メール認証
        _issue_verification(user)
        flash(
            "アカウントを作成しました。確認メールを送信しました。メールに記載のリンクで認証してください。",
            "success",
        )
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # ブルートフォース対策: IPあたり5分間に5回まで
        client_key = request.remote_addr or "unknown"
        try:
            login_rate_limiter.hit(client_key)
        except RateLimitExceeded as e:
            flash(str(e), "error")
            return render_template("auth/login.html")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_rate_limiter.reset(client_key)
            login_user(user)
            migrate_guest_wordlists(user)
            flash("ログインしました。", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("メールアドレスまたはパスワードが正しくありません。", "error")

    return render_template("auth/login.html")


@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    """メール認証リンクの確認。"""
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        flash("認証リンクが無効です。", "error")
        return redirect(url_for("auth.login"))

    if _is_token_expired(user.verification_token_expiry):
        flash("認証リンクの有効期限が切れています。再送してください。", "error")
        return redirect(url_for("main.resend_verification"))

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    db.session.commit()
    login_user(user)
    flash("メール認証が完了しました。", "success")
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/resend-verification")
@login_required
def resend_verification():
    """確認メールを再送する。"""
    if current_user.email_verified:
        flash("既にメール認証済みです。", "info")
        return redirect(url_for("main.dashboard"))
    _issue_verification(current_user)
    flash("確認メールを再送しました。", "success")
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "success")
    return redirect(url_for("main.index"))
