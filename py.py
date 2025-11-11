import requests
import pandas as pd
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import smtplib
import io
import os
import time

# -----------------------------
# EMAIL CONFIGURATION (from GitHub Secrets)
# -----------------------------
SENDER = os.getenv("EMAIL_USER")
RECEIVER = os.getenv("EMAIL_RECEIVER", SENDER)
PASSWORD = os.getenv("EMAIL_PASS")

# -----------------------------
# FETCH NSE DATA WITH RETRY
# -----------------------------
def fetch_nse_data():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/"
    }

    url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"

    session = requests.Session()

    for attempt in range(5):  # retry 5 times
        try:
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {e}")
            time.sleep(3)

    raise Exception("❌ Failed to fetch NSE data after multiple attempts.")

# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main():
    data = fetch_nse_data()
    df = pd.DataFrame(data['allSec']['data'])[:2]  # top 2 gainers

    # -----------------------------
    # PLOT CHART AND SAVE TO MEMORY
    # -----------------------------
    sns.set(style="whitegrid")

    price_df = df.melt(
        id_vars=["symbol", "perChange"],
        value_vars=["open_price", "high_price", "ltp"],
        var_name="price_type",
        value_name="price"
    )

    fig, ax1 = plt.subplots(figsize=(9, 5))

    bars = sns.barplot(data=price_df, x="symbol", y="price", hue="price_type", ax=ax1)
    ax1.set_ylabel("Price (₹)", color="blue")
    ax1.tick_params(axis='y', labelcolor="blue")

    for container in bars.containers:
        bars.bar_label(
            container,
            fmt='%.2f',
            label_type='center',
            fontsize=9,
            color='white',
            weight='bold'
        )

    plt.title("Stock Comparison: Open, High, LTP")
    plt.tight_layout()

    # Save figure to bytes buffer (no disk write)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close(fig)

    # -----------------------------
    # CREATE EMAIL CONTENT
    # -----------------------------
    msg = MIMEMultipart()
    msg["Subject"] = f"📈 Daily NSE Top Gainers Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER

    body_text = f"""
Hello 👋,

Here’s your Daily NSE Top Gainers Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}).

Top 1: {df['symbol'][0]}  
Top 2: {df['symbol'][1]}

Attached below is today’s stock performance chart.

Best regards,  
Your Daily Stock Bot 🤖
"""
    msg.attach(MIMEText(body_text, "plain"))

    # Attach chart image
    image = MIMEImage(buffer.getvalue(), name="chart.png")
    msg.attach(image)

    # -----------------------------
    # SEND EMAIL
    # -----------------------------
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
        print("✅ Mail sent successfully with chart!")
    except Exception as e:
        print("❌ Failed to send email:", e)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    main()
