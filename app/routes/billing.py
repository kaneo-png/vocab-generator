from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.services.billing_service import BillingService, BillingServiceError

billing_bp = Blueprint("billing", __name__)


@billing_bp.route("/billing/plans")
@login_required
def plans():
    """プラン選択ページ。"""
    return render_template("billing/plans.html")


@billing_bp.route("/billing/checkout/<plan>")
@login_required
def checkout(plan: str):
    """Stripe Checkoutセッションを作成してリダイレクトする。"""
    if plan not in ("ad_free", "premium"):
        flash("不正なプランです。", "error")
        return redirect(url_for("billing.plans"))

    try:
        billing = BillingService()
        checkout_url = billing.create_checkout_session(current_user, plan)
        return redirect(checkout_url)
    except BillingServiceError as e:
        flash(str(e), "error")
        return redirect(url_for("billing.plans"))


@billing_bp.route("/billing/success")
@login_required
def success():
    """決済成功ページ。"""
    return render_template("billing/success.html")


@billing_bp.route("/billing/cancel")
@login_required
def cancel():
    """決済キャンセルページ。"""
    flash("決済がキャンセルされました。", "info")
    return redirect(url_for("billing.plans"))


@billing_bp.route("/billing/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    """Stripe Webhook受信エンドポイント。"""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        billing = BillingService()
        event = billing.handle_webhook(payload, sig_header)
    except BillingServiceError as e:
        return jsonify({"error": str(e)}), 400

    # サブスクリプション更新イベントを処理
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        if user_id and plan:
            from app.models.user import User

            user = db.session.get(User, int(user_id))
            if user:
                user.plan = plan
                db.session.commit()

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        # 解約・キャンセル時の処理
        if subscription.get("status") == "canceled":
            # メタデータからユーザーを特定してfreeに戻す
            # 実際の運用ではStripe Customer IDをユーザーに紐づける必要がある
            pass

    return jsonify({"received": True}), 200