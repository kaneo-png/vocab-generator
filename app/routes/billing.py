from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
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
    from app.models.user import User

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        # 決済完了: プラン昇格 + Stripe Customer ID保存
        user_id = obj.get("metadata", {}).get("user_id")
        plan = obj.get("metadata", {}).get("plan")
        customer_id = obj.get("customer")
        if user_id and plan:
            user = db.session.get(User, int(user_id))
            if user:
                user.plan = plan
                if customer_id:
                    user.stripe_customer_id = customer_id
                db.session.commit()

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        # 解約・未払い時は free に戻す
        status = obj.get("status")
        if event_type == "customer.subscription.deleted" or status in (
            "canceled",
            "unpaid",
            "incomplete_expired",
        ):
            customer_id = obj.get("customer")
            if customer_id:
                user = User.query.filter_by(stripe_customer_id=customer_id).first()
                if user and user.plan != "free":
                    user.plan = "free"
                    db.session.commit()
                    current_app.logger.info(
                        f"ユーザー {user.id} をサブスク解除により free に戻しました"
                    )

    return jsonify({"received": True}), 200