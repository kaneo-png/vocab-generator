import stripe
from flask import current_app


class BillingServiceError(Exception):
    """決済サービスで発生するエラー。"""


class BillingService:
    """Stripeを使ったサブスクリプション管理。"""

    def __init__(self):
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

    def create_checkout_session(self, user, plan: str) -> str:
        """
        Stripe Checkoutセッションを作成し、URLを返す。

        Args:
            user: 対象ユーザー
            plan: "ad_free" または "premium"

        Returns:
            CheckoutセッションのURL
        """
        price_id = self._get_price_id(plan)
        if not price_id:
            raise BillingServiceError(
                f"プラン '{plan}' のStripe Price IDが設定されていません。"
            )

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=user.email,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=current_app.config.get(
                    "STRIPE_SUCCESS_URL", "http://localhost:5000/billing/success"
                ),
                cancel_url=current_app.config.get(
                    "STRIPE_CANCEL_URL", "http://localhost:5000/billing/plans"
                ),
                metadata={"user_id": str(user.id), "plan": plan},
            )
            return session.url
        except stripe.error.StripeError as e:
            raise BillingServiceError(f"Stripeエラー: {e}")

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """
        Stripe Webhookイベントを検証・処理する。

        Returns:
            処理したイベント情報
        """
        webhook_secret = current_app.config["STRIPE_WEBHOOK_SECRET"]
        if not webhook_secret:
            raise BillingServiceError("STRIPE_WEBHOOK_SECRET が設定されていません。")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            raise BillingServiceError(f"Webhook検証エラー: {e}")

        return event

    def _get_price_id(self, plan: str) -> str:
        """プラン名に対応するStripe Price IDを返す。"""
        price_ids = {
            "ad_free": current_app.config["STRIPE_PRICE_AD_FREE"],
            "premium": current_app.config["STRIPE_PRICE_PREMIUM"],
        }
        return price_ids.get(plan, "")