"""Gmail SMTP로 알림 메일을 보낸다."""

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv(override=True)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_TO = os.getenv("NOTIFY_TO") or GMAIL_ADDRESS


def send(subject: str, body: str, html: bool = False) -> None:
    """메일 한 통을 보낸다."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise ValueError(
            ".env에 GMAIL_ADDRESS와 GMAIL_APP_PASSWORD를 설정하세요."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Job Jarvis <{GMAIL_ADDRESS}>"
    msg["To"] = NOTIFY_TO

    if html:
        msg.set_content("HTML 메일입니다. HTML을 지원하는 클라이언트에서 확인하세요.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    # 465 포트 + SSL. Gmail 표준 방식이다.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print(f"메일 발송 완료 → {NOTIFY_TO}")


if __name__ == "__main__":
    send(
        "[Job Jarvis] 테스트 메일",
        "메일 발송이 정상적으로 설정되었습니다.\n\n이 메일이 보이면 5단계 준비 완료입니다.",
    )