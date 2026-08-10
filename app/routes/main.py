from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.wordlist import WordList

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """ランディングページ。未ログインでもアクセス可能。"""
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """ダッシュボード。生成した単語帳の一覧とプラン情報を表示。"""
    wordlists = (
        WordList.query.filter_by(user_id=current_user.id)
        .order_by(WordList.created_at.desc())
        .all()
    )
    return render_template(
        "dashboard.html",
        wordlists=wordlists,
        monthly_limit=current_user.get_monthly_limit(),
        monthly_count=current_user.monthly_generation_count,
    )