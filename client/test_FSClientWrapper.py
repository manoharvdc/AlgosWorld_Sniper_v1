import ast
import hashlib
import os
from dotenv import load_dotenv

import requests

# Load environment variables from .env file
load_dotenv()

BASE_URL = "http://127.0.0.1:9000/Firstock"  # Base URL of the FastAPI server


def encode_pwd(pwd):
    return hashlib.sha256(pwd.encode())


def test_login():
    """
    Test the login endpoint.
    """
    global user_details

    response = requests.post(f"{BASE_URL}/login", json=user_details)
    # print("Login Response status_code Code:", response.status_code)
    # print("Login Response text Code:", response.text)
    # print("Login Response content Code:", response.content)
    jsonString = response.content.decode("utf-8")

    finalResult = ast.literal_eval(jsonString)
    print("Login Response:", finalResult)
    assert response.status_code == 200, "Login failed"
    user_details["access_token"] = finalResult.get("data", {}).get("susertoken")
    print("Access Token:", user_details["access_token"])


def test_place_order():
    """
    Test the placeOrder endpoint.
    """

    payload = {'tradingSymbol': 'NIFTY05JUN25C24600',
               'exchange': 'NFO', 'price': '0.0', 'transactionType': 'S',
               'priceType': 'MKT', 'triggerPrice': 'None', 'quantity': '75',
               'product': 'I', 'retention': 'DAY',
               'remarks': 'AWTest',
               'userId': user_details["userId"],
               'jKey': user_details["access_token"]
               }

    response = requests.post(f"{BASE_URL}/placeOrder", json=payload)
    print("Place Order Response:", response.json())
    assert response.status_code == 200, "Place order failed"
    # get ordernum and store in user_details
    jsonString = response.content.decode("utf-8")
    order_num = ast.literal_eval(jsonString).get("data", {}).get("orderNumber")
    user_details["orderNumber"] = order_num


def test_get_order():
    payload = {'orderNumber': user_details["orderNumber"],
               'userId': user_details["userId"],
               'jKey': user_details["access_token"]}
    response = requests.post(f"{BASE_URL}/singleOrderHistory", json=payload)
    print("Get Order Response:", response.json())
    assert response.status_code == 200, "Get limits failed"


def test_get_limits():
    """
    Test the limit endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
    }
    response = requests.post(f"{BASE_URL}/limit", json=payload)
    print("Get Limits Response:", response.json())
    assert response.status_code == 200, "Get limits failed"


def test_cancel_order():
    """
    Test the cancelOrder endpoint.
    """
    payload = {
        "order_id": "12345",
        "quantity": 10,
        "price": 150.5
    }
    response = requests.post(f"{BASE_URL}/cancelOrder", json=payload)
    print("Cancel Order Response:", response.json())
    assert response.status_code == 200, "Cancel order failed"


def test_get_order_book():
    """
    Test the orderBook endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
    }
    response = requests.post(f"{BASE_URL}/orderBook", json=payload)
    print("Get Order Book Response:", response.json())
    assert response.status_code == 200, "Get order book failed"


def test_get_position_book():
    """
    Test the orderBook endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
    }
    response = requests.post(f"{BASE_URL}/positionBook", json=payload)
    print("Get positionBook Book Response:", response.json())
    assert response.status_code == 200, "Get positionBook book failed"


def test_get_quote_ltp():
    """
    Test the quote ltp endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
        "exchange": "NFO",
        "tradingSymbol": "NIFTY12JUN25C24600",
    }
    response = requests.post(f"{BASE_URL}/getQuote/ltp", json=payload)
    print("Get quote ltp Response:", response.json())
    assert response.status_code == 200, "Get order book failed"


def test_get_multiQuote_ltp():
    """
    Test the quote ltp endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
        "data": [
            {
                "exchange": "NFO",
                "tradingSymbol": "NIFTY24DEC25C25000",
            },
            {
                "exchange": "NFO",
                "tradingSymbol": "NIFTY24DEC25P25000",
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/getMultiQuotes/ltp", json=payload)
    print("Get getMultiQuotes ltp Response:", response.json())
    assert response.status_code == 200, "Get getMultiQuotes failed"


def test_get_quote():
    """
    Test the quote ltp endpoint.
    """
    payload = {
        "userId": user_details["userId"],
        "jKey": user_details["access_token"],
        "exchange": "NFO",
        "tradingSymbol": "NIFTY12JUN25C24600",
    }
    response = requests.post(f"{BASE_URL}/getQuote", json=payload)
    print("Get quote Response:", response.json())
    assert response.status_code == 200, "Get order book failed"


def init_user():
    global user_details
    
    # Load credentials from environment variables
    user_id = os.getenv("FS_USER_ID")
    password = os.getenv("FS_PASSWORD")
    totp = os.getenv("FS_TOTP")
    vendor_code = os.getenv("FS_VENDOR_CODE")
    api_key = os.getenv("FS_API_KEY")
    
    # Check if all required environment variables are set
    if not all([user_id, password, totp, vendor_code, api_key]):
        raise ValueError(
            "Missing required environment variables. Please ensure the following are set:\n"
            "FS_USER_ID, FS_PASSWORD, FS_TOTP, FS_VENDOR_CODE, FS_API_KEY\n"
            "Copy .env.example to .env and fill in your credentials."
        )
    
    encryptedPassword = encode_pwd(password)
    user_details = {
        "userId": user_id,
        "password": encryptedPassword.hexdigest(),
        "TOTP": totp,
        "vendorCode": vendor_code,
        "apiKey": api_key
    }


if __name__ == "__main__":
    print("Testing Firststock API endpoints...")
    init_user()
    test_login()
    test_get_limits()

    # test_get_quote_ltp()
    test_get_multiQuote_ltp()
    # test_get_quote()
    test_get_position_book()
    # test_place_order()
    # test_get_order()
    # test_get_order_book()
    # test_get_limits()
    # test_cancel_order()
    print("All tests completed.")
