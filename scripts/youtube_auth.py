#!/usr/bin/env python3
"""
Одноразовый скрипт для получения YouTube OAuth2 Refresh Token.

Использование:
    1. Зайди в Google Cloud Console → APIs & Services → Credentials
    2. Создай OAuth 2.0 Client ID (тип: Desktop App)
    3. Запусти этот скрипт:
       python scripts/youtube_auth.py --client-id=ВАШ_CLIENT_ID --client-secret=ВАШ_CLIENT_SECRET
    4. Откроется браузер — авторизуйся в Google-аккаунте
    5. Скрипт выведет REFRESH_TOKEN — добавь его в .env
"""

import argparse
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

import requests

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
REDIRECT_PORT = 8090
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class CallbackHandler(BaseHTTPRequestHandler):
    """Ловит callback от Google OAuth2."""

    auth_code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        if "code" in query:
            CallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h2>✅ Авторизация успешна!</h2>"
                "<p>Можете закрыть эту вкладку и вернуться в терминал.</p>"
                "</body></html>".encode("utf-8")
            )
        else:
            error = query.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>❌ Ошибка: {error}</h2></body></html>".encode("utf-8")
            )

    def log_message(self, format, *args):
        pass  # тихий сервер


def get_auth_code(client_id):
    """Открывает браузер для авторизации и ждёт callback."""
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    print(f"\n🌐 Открываю браузер для авторизации...")
    print(f"   Если браузер не открылся, перейдите по ссылке:\n   {auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server.handle_request()

    return CallbackHandler.auth_code


def exchange_code(client_id, client_secret, code):
    """Обменивает auth code на access + refresh tokens."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Получить YouTube OAuth2 Refresh Token")
    parser.add_argument("--client-id", required=True, help="OAuth2 Client ID")
    parser.add_argument("--client-secret", required=True, help="OAuth2 Client Secret")
    args = parser.parse_args()

    print("=" * 50)
    print("🔑 YouTube OAuth2 — получение Refresh Token")
    print("=" * 50)

    code = get_auth_code(args.client_id)

    if not code:
        print("❌ Не удалось получить auth code")
        return

    print("✅ Auth code получен, обмениваю на токены...")

    tokens = exchange_code(args.client_id, args.client_secret, code)

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if not refresh_token:
        print("❌ Google не вернул refresh_token.")
        print("   Попробуйте отозвать доступ на https://myaccount.google.com/permissions")
        print("   и запустить скрипт снова.")
        return

    print("\n" + "=" * 50)
    print("✅ ГОТОВО! Добавьте в .env:")
    print("=" * 50)
    print(f"\nYOUTUBE_CLIENT_ID={args.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={args.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={refresh_token}")
    print()


if __name__ == "__main__":
    main()
