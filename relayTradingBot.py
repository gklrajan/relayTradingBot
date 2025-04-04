import requests
import imaplib
import email
from email.header import decode_header
import json
import time
import os
import sys
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import example_utils

# Fetching email credentials from environment variables
SENDER_EMAIL = os.getenv('EMAIL') # Your gmail
SENDER_PASSWORD = os.getenv('APP_PASSWORD') # Your gmail app password
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

# All time periods are for example.
CHECK_INTERVAL = 15  # Check every 15 seconds
RECONNECT_INTERVAL = 580  # Reconnect every hour
KEEP_ALIVE_INTERVAL = 180  # Send a NOOP command every 5 minutes

if not SENDER_EMAIL or not SENDER_PASSWORD:
    raise ValueError("Email credentials not found in environment variables.")

# Fetching exchange credentials from environment variables
private_key = os.getenv('secret_key') # Shh...
account_address = os.getenv('account_address') # Shh...

if not private_key or not account_address:
    raise ValueError("Private key or account address not found in environment variables.")

# Hyperliquid configuration
vault_address = "" # Your vault address. It's as straightforward to use it directly with an account. The vault setup is simly more flexible.

# Setup Hyperliquid Exchange with Vault
address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)
agent_exchange = Exchange(exchange.wallet, exchange.base_url, vault_address=vault_address)

# Telegram bot credentials
bot_token = '' # Your Telegram bot credential. Use BotFather to generate one
chat_id = '' # Telegram bot credential

# Initialize balance
balance = 100.0 #
position_closed = False  # Flag to track whether the position is closed

def send_telegram_message(message, tag="Trade Update"):
    """Send a message to the Telegram bot with a specified tag."""
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': f"{tag}: {message}"
    }
    try:
        response = requests.post(telegram_url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def has_open_positions(agent_exchange, vault_address):
    """Check if there are any open positions."""
    try:
        user_state = agent_exchange.info.user_state(vault_address)
        positions = user_state.get("assetPositions", [])
        return len(positions) > 0
    except Exception as e:
        error_message = f"Error checking open positions: {e}"
        print(error_message)
        send_telegram_message(error_message)  # Send the error to Telegram
        return True  # Assume open positions on error

def query_balance():
    """Query the balance from the Hyperliquid exchange and update it."""
    global balance
    try:
        if not has_open_positions(agent_exchange, vault_address):  # No open positions, update the balance
            balance_info = agent_exchange.info.user_state(vault_address)
            if 'marginSummary' in balance_info:
                balance = float(balance_info['marginSummary']['accountValue'])
                print(f"Balance updated: {balance}")
            else:
                print("Failed to retrieve balance information.")
        else:
            print("Open positions exist, balance not updated.")
    except Exception as e:
        print(f"Error querying balance: {e}")
        send_telegram_message(f"Error querying balance: {e}", "Trade Update")

def execute_market_order(symbol, action, contracts):
    """Execute a market order on the Hyperliquid exchange."""
    global balance  # Declare balance as global to modify the global variable
    global position_closed  # Access the position_closed flag
    tag = "Trade Update"
    is_buy = action.lower() == 'buy'

    # If it's a buy order, reset the position_closed flag
    if is_buy:
        position_closed = False

    # Calculate order size directly from contracts
    quantity = round(contracts * 5, 5) # This depends on how you set up your signal, and the size and leverage you want to use

    print(f"Executing {action} order for {quantity} {symbol}.")
    send_telegram_message(f"Executing {action} order for {quantity} {symbol}.", tag)

    if symbol == "BTCUSD":
        symbol = "BTC"

    agent_exchange.session = requests.Session()

    try:
        order_result = agent_exchange.market_open(symbol, is_buy, quantity, None, 0.01)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    msg = f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}'
                    print(msg)
                    send_telegram_message(msg, tag)
                except KeyError:
                    error_msg = f'Error: {status["error"]}'
                    print(error_msg)
                    send_telegram_message(error_msg, tag)
        else:
            error_msg = f"Market order failed: {order_result}"
            print(error_msg)
            send_telegram_message(error_msg, tag)
    except Exception as e:
        error_msg = f"Error executing order for {symbol}: {e}"
        print(error_msg)
        send_telegram_message(error_msg, tag)
    finally:
        agent_exchange.session.close()

    time.sleep(3)

def execute_market_close(agent_exchange, symbol):
    """Close 100% of the position and notify via Telegram."""
    global position_closed  # Access the position_closed flag
    tag = "Trade Update"
    message = f"Market Close all {symbol}."
    print(message)
    send_telegram_message(message, tag)

    if symbol == "BTCUSD":
        symbol = "BTC"

    order_result = agent_exchange.market_close(symbol)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                msg = f'Order #{filled["oid"]} closed {filled["totalSz"]} @{filled["avgPx"]}'
                print(msg)
                send_telegram_message(msg, tag)
            except KeyError:
                error_msg = f'Error: {status["error"]}'
                print(error_msg)
                send_telegram_message(error_msg, tag)
    else:
        error_msg = f"Market close failed: {order_result}"
        print(error_msg)
        send_telegram_message(error_msg, tag)

    # Set the flag to indicate the position is closed
    position_closed = True
    time.sleep(3)

def process_json_data(data):
    global position_closed  # Access the position_closed flag
    try:
        # Identify the strategy type
        strategy_name = data.get("strategy", {}).get("name")
        action = data.get("order", {}).get("action")
        symbol = data.get("order", {}).get("filled_on")
        contracts = float(data.get("order", {}).get("contracts"))

        if strategy_name == "MY TradingView Strategy XYZ":  # Replace with your TradingView strategy name
            new_position_size = float(data.get("position", {}).get("new_strategy_position", 0))
            current_position_size = new_position_size - contracts

            if action and symbol and contracts:
                # If the action is "sell" and the position is not already closed
                if action.lower() == "sell" and not position_closed:
                    print(f"Sell signal received. Closing all positions for {symbol}.")
                    send_telegram_message(f"Sell signal received. Closing all positions for {symbol}.", "Trade Update")
                    execute_market_close(agent_exchange, symbol)
                elif action.lower() == "buy":
                    # Normal buy order execution
                    if (current_position_size > 0 and new_position_size < 0 and abs(new_position_size) > abs(
                            current_position_size)) or (
                            current_position_size < 0 and new_position_size > 0 and abs(new_position_size) > abs(
                        current_position_size)):
                        execute_market_close(agent_exchange, symbol)
                        remaining_size = abs(new_position_size) - abs(current_position_size)
                        if remaining_size > 0:
                            execute_market_order(symbol, action, remaining_size)
                        else:
                            print(f"Position fully closed, no new order placed.")
                            send_telegram_message("Position fully closed, no new order placed.", "Trade Update")
                    else:
                        execute_market_order(symbol, action, contracts)

    except Exception as e:
        error_msg = f"Error processing JSON: {e}"
        print(error_msg)
        send_telegram_message(error_msg, "Trade Update")


def check_email(mail):
    try:
        mail.select("inbox")
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, '(RFC822)')
            if status == 'OK':
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = decode_header(msg["Subject"])[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()
                        print(f"Email subject: {subject}")
                        subject = subject.replace("Alert:", "").strip()
                        subject = " ".join(subject.split())

                        try:
                            data = json.loads(subject)
                            process_json_data(data)
                            mail.store(e_id, '+FLAGS', '\\Seen')
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON from the subject: {e}")
                            mail.store(e_id, '+FLAGS', '\\Seen')
                            continue
    except Exception as e:
        print(f"Error checking email: {e}")
        send_telegram_message(f"Error checking email: {e}")
        raise  # Re-raise the exception to handle it in the main loop

def main():
    global balance
    reconnect_time = time.time() + RECONNECT_INTERVAL
    last_keep_alive = time.time()

    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(SENDER_EMAIL, SENDER_PASSWORD)

            while time.time() < reconnect_time:
                query_balance()  # Query and update balance if no open positions
                check_email(mail)
                if time.time() - last_keep_alive > KEEP_ALIVE_INTERVAL:
                    mail.noop()
                    last_keep_alive = time.time()

                time.sleep(CHECK_INTERVAL)

            mail.logout()
            reconnect_time = time.time() + RECONNECT_INTERVAL

        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, ConnectionResetError) as e:
            print(f"IMAP connection error: {e}")
            send_telegram_message(f"IMAP connection error: {e}")
            time.sleep(15)  # Brief wait before attempting to reconnect
            continue  # Retry connection loop

        except Exception as e:
            print(f"Unexpected error: {e}")
            send_telegram_message(f"Unexpected error: {e}")
            time.sleep(15)

            # Restart the script
            os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    main()
