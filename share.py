# ================================================
# PolicyGuard — ngrok tunnel
# Run this to get a public URL for your professor
# Usage: python share.py
# ================================================

from pyngrok import ngrok
import time
import os

print("=" * 50)
print("  PolicyGuard — Public Share")
print("=" * 50)

# Read auth token from env if set
auth_token = os.getenv("NGROK_AUTH_TOKEN")
if auth_token:
    ngrok.set_auth_token(auth_token)

# Open tunnel to the running app on port 8501
print("\nOpening tunnel to http://localhost:8501 ...")
tunnel = ngrok.connect(8501, "http")

print("\n✅ Your public URL is:")
print(f"\n   👉  {tunnel.public_url}\n")
print("Share this URL with your professor.")
print("The tunnel stays open as long as this script runs.")
print("\nPress Ctrl+C to stop sharing.\n")
print("=" * 50)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nClosing tunnel...")
    ngrok.disconnect(tunnel.public_url)
    ngrok.kill()
    print("✅ Tunnel closed.")
