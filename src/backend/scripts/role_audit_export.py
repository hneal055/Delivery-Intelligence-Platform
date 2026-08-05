import asyncio
import csv
import smtplib
import os
from collections import Counter
from datetime import datetime
from email.message import EmailMessage
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User


# Leave False until SMTP login testing succeeds
SEND_EMAIL = True

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = os.getenv("AUDIT_EMAIL")
SENDER_PASSWORD = os.getenv("AUDIT_PASSWORD")

RECIPIENT_EMAILS = [
    "howard@scenereaderstudio.com"
]


def test_smtp_connection():
    try:
        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT,
        ) as server:

            server.starttls()

            print(
                "\n✅ SMTP connection successful"
            )

    except Exception as exc:
        print(
            f"\n❌ SMTP connection failed: {exc}"
        )


def test_smtp_login():
    try:
        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT,
        ) as server:

            server.starttls()

            server.login(
                SENDER_EMAIL,
                SENDER_PASSWORD,
            )

            print(
                "\n✅ SMTP login successful"
            )

    except Exception as exc:
        print(
            f"\n❌ SMTP login failed: {exc}"
        )


def send_email(
    summary_file,
    latest_file,
):
    message = EmailMessage()

    message["Subject"] = (
        "Delivery Intelligence Platform - User Role Audit"
    )

    message["From"] = SENDER_EMAIL

    message["To"] = ", ".join(
        RECIPIENT_EMAILS
    )

    with open(
        summary_file,
        "r",
        encoding="utf-8",
    ) as file:

        body = file.read()

    message.set_content(body)

    with open(
        latest_file,
        "rb",
    ) as file:

        message.add_attachment(
            file.read(),
            maintype="application",
            subtype="octet-stream",
            filename=latest_file.name,
        )

    with smtplib.SMTP(
        SMTP_SERVER,
        SMTP_PORT,
    ) as server:

        server.starttls()

        server.login(
            SENDER_EMAIL,
            SENDER_PASSWORD,
        )

        server.send_message(message)


def preview_email(summary_file):
    print("\nEMAIL PREVIEW")
    print("=" * 60)

    with open(
        summary_file,
        "r",
        encoding="utf-8",
    ) as file:

        print(file.read())

    print("=" * 60)


async def main():
    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User)
        )

        users = result.scalars().all()

        timestamp = datetime.now().strftime(
            "%Y_%m_%d_%H%M%S"
        )

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # Historical audit report
        csv_file = (
            reports_dir
            / f"user_role_audit_{timestamp}.csv"
        )

        with open(
            csv_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "id",
                    "username",
                    "email",
                    "role",
                    "is_active",
                ]
            )

            for user in users:
                writer.writerow(
                    [
                        user.id,
                        user.username,
                        user.email,
                        user.role,
                        user.is_active,
                    ]
                )

        # Latest summary report
        latest_file = (
            reports_dir
            / "user_role_summary_latest.csv"
        )

        with open(
            latest_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "id",
                    "username",
                    "email",
                    "role",
                    "is_active",
                ]
            )

            for user in users:
                writer.writerow(
                    [
                        user.id,
                        user.username,
                        user.email,
                        user.role,
                        user.is_active,
                    ]
                )

        role_counts = Counter(
            user.role for user in users
        )

        # Email-ready summary
        summary_file = (
            reports_dir
            / "user_role_summary_email.txt"
        )

        with open(
            summary_file,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(
                "Delivery Intelligence Platform\n"
            )

            file.write(
                "User Role Audit Summary\n"
            )

            file.write(
                "=" * 40 + "\n\n"
            )

            file.write(
                f"Audit Date: {timestamp}\n"
            )

            file.write(
                f"Total Users: {len(users)}\n\n"
            )

            file.write(
                "Role Breakdown\n"
            )

            file.write(
                "-" * 20 + "\n"
            )

            for role, count in sorted(
                role_counts.items()
            ):
                file.write(
                    f"{role.upper()}: {count}\n"
                )

            active_users = sum(
                1
                for user in users
                if user.is_active
            )

            inactive_users = sum(
                1
                for user in users
                if not user.is_active
            )

            file.write(
                "\nAccount Status\n"
            )

            file.write(
                "-" * 20 + "\n"
            )

            file.write(
                f"Active Users: {active_users}\n"
            )

            file.write(
                f"Inactive Users: {inactive_users}\n"
            )

            file.write(
                "\nGenerated by role_audit_export.py\n"
            )

        print("\nROLE SUMMARY")
        print("=" * 40)
        print(
            f"Total Users : {len(users)}"
        )

        for role, count in sorted(
            role_counts.items()
        ):
            print(
                f"{role.upper():<15} {count}"
            )

        print("=" * 40)

        print(
            f"Historical Report : {csv_file}"
        )

        print(
            f"Latest Report     : {latest_file}"
        )

        print(
            f"Email Summary     : {summary_file}"
        )

        preview_email(summary_file)

        test_smtp_connection()

        test_smtp_login()

        if SEND_EMAIL:
            send_email(
                summary_file,
                latest_file,
            )
            print("\n✅ Email sent.")


if __name__ == "__main__":
    asyncio.run(main())