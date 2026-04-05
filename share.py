# ================================================
# PolicyGuard — ngrok tunnel
# Usage: python share.py
# ================================================

from pyngrok import ngrok
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 55)
print("  PolicyGuard — Public Share")
print("=" * 55)

auth_token = os.getenv("NGROK_AUTH_TOKEN")
if auth_token:
    ngrok.set_auth_token(auth_token)

print("\nOpening tunnel to http://localhost:8501 ...")
tunnel = ngrok.connect(8501, "http")

public_url = tunnel.public_url
share_url  = public_url + "/?ngrok-skip-browser-warning=true"

print("\n✅ Tunnel is live!\n")
print(f"   Your URL   : {public_url}")
print(f"   Share this : {share_url}")
print("\nSend the 'Share this' link to your professor.")
print("The tunnel stays open as long as this script runs.")
print("\nPress Ctrl+C to stop.\n")
print("=" * 55)

try:
    input()
except KeyboardInterrupt:
    pass
finally:
    ngrok.disconnect(public_url)
    ngrok.kill()
    print("\n✅ Tunnel closed.")
