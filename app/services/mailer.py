"""メール送信の抽象化。

開発・ベータではコンソールに出力し、本番ではSendGrid/SMTP等に差し替える。
MAILER_BACKEND で切替（console がデフォルト）。
"""
import logging
from flask import current_app, url_for

logger = logging.getLogger(__name__)


def send_verification_email(user, token: str) -> None:
    """メール認証リンクを送信する。"""
    verify_url = url_for("auth.verify_email", token=token, _external=True)

    subject = "【単語帳ジェネレーター】メールアドレスの確認"
    body = (
        f"{user.email} さん\n\n"
        f"アカウント作成ありがとうございます。\n"
        f"以下のリンクをクリックして、メールアドレスの認証を完了してください。\n\n"
        f"{verify_url}\n\n"
        f"※ このリンクは24時間有効です。\n"
        f"※ 心当たりがない場合はこのメールを無視してください。\n"
    )

    backend = current_app.config.get("MAILER_BACKEND", "console")
    if backend == "sendgrid":
        _send_via_sendgrid(user.email, subject, body)
    elif backend == "smtp":
        _send_via_smtp(user.email, subject, body)
    else:
        _send_via_console(user.email, subject, body)


def _send_via_console(to_email: str, subject: str, body: str) -> None:
    """開発用: コンソールにメール内容を出力する。"""
    print("\n" + "=" * 60)
    print(f"[DEV MAIL] To: {to_email}")
    print(f"[DEV MAIL] Subject: {subject}")
    print(body)
    print("=" * 60 + "\n")


def _send_via_sendgrid(to_email: str, subject: str, body: str) -> None:
    """SendGridで送信する（本番用）。sendgridパッケージが必要。"""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
    except ImportError:
        logger.error("sendgrid パッケージがインストールされていません。")
        _send_via_console(to_email, subject, body)
        return

    api_key = current_app.config.get("SENDGRID_API_KEY", "")
    if not api_key:
        logger.error("SENDGRID_API_KEY が設定されていません。")
        _send_via_console(to_email, subject, body)
        return

    message = Mail(
        from_email=current_app.config.get("MAIL_FROM", "noreply@example.com"),
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    sg.send(message)


def _send_via_smtp(to_email: str, subject: str, body: str) -> None:
    """SMTPで送信する（本番用）。"""
    import smtplib
    from email.mime.text import MIMEText

    host = current_app.config.get("SMTP_HOST", "")
    port = current_app.config.get("SMTP_PORT", 587)
    username = current_app.config.get("SMTP_USER", "")
    password = current_app.config.get("SMTP_PASSWORD", "")
    from_addr = current_app.config.get("MAIL_FROM", username)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if username:
                server.login(username, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
    except Exception as e:
        logger.error(f"SMTP送信に失敗: {e}")
