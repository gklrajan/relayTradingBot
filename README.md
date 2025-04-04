# relayTradingBot

relayTradingBot superpowers your pine scripts by bridging the gap between TV webhooks and unsupported exchanges using Gmail as a simple relay layer.

**Who is it for?** 

If you use pine scripting to develop algorithms as a hobby (or even professionally) but TradingView doesn't natively support integration with your fav exchange, relayTradingBot's approach can come handy. If your fav exchange happens to be Hyperliquid, that's even better as this script utilizes the Hyperliquid API. It processes TradingView alerts, interprets trading signals, and executes market orders on Hyperliquid DEX. Ideally, it is only suitable for high timeframe strategies and not for low timeframe strategies. It is definitely not usable for low latency, high frequency trading.

Note: This project was initially created as a weekend experiment. However, a version of this setup has been reliably running on my personal server for over six months. While the script has proven stable in my personal use, it has only been tested with a limited amount of capital (because i'm poor :D). Therefore, thorough testing and due diligence are strongly recommended before deploying this system with significant funds. This script is provided publicly primarily for methodological reference.


**Features**:
- Reads TradingView alerts sent to Gmail and processes trading signals.
- Executes buy and sell orders on Hyperliquid using their API.
- Updates balance dynamically when positions are closed.
- Sends real-time Telegram notifications for updates and errors.

**Setup Instructions**
- Clone the repository.
- Install dependencies: pip install -r requirements.txt
- Set the environment variables:
  EMAIL: Your Gmail address for receiving alerts.
  APP_PASSWORD: Gmail app-specific password. (Enable 2-Step Verification in your Google Account Security. Go to App Passwords and generate one for "Mail."Use this password.)
  secret_key: Hyperliquid private API key.
  account_address: Hyperliquid account address.
  BOT_TOKEN: Telegram bot token.
  CHAT_ID: Telegram chat ID.
- Now, with all you credentials updated and trading settings customized to your taste, you're ready to run this script on your server!

**Security Tips** 
- Use environment variables to store sensitive credentials. 
- Use a dedicated Gmail account with 2FA enabled.
- Restrict Telegram bot permissions to your chat only.

**Disclaimer: relayTradingBot is provided "as-is" for reference purposes only. Use it at your own risk. The author assumes no responsibility for any financial losses, system failures, misconfigurations, or other issues arising from the use of this tool. Users are encouraged to thoroughly review and test the code before deploying it in a live environment.**

## License
This project is licensed under the MIT License - see the LICENSE file for details.

