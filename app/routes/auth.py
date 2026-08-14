from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.services.rate_limit import login_rate_limiter, RateLimitExceeded

auth_bp = Blueprint("auth", __name__)


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
        flash("アカウントを作成しました。", "success")
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
            flash("ログインしました。", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("メールアドレスまたはパスワードが正しくありません。", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "success")
    return redirect(url_for("main.index"))