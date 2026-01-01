import logging
import os
import traceback
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# Statistics tracking
stats = {
    "total_requests": 0,
    "by_broker": defaultdict(int),
    "by_method": defaultdict(int),
    "by_action": defaultdict(int),
    "by_status": defaultdict(int),
    "start_time": datetime.now().isoformat(),
    "last_request_time": None,
    "last_request_received": None,
    "last_response_sent": None,
    "total_response_time_ms": 0,
    "avg_response_time_ms": 0,
    "min_response_time_ms": None,
    "max_response_time_ms": None,
    "errors": 0,
    "success": 0
}


def get_logger(log_file_name, logs_folder="logs"):
    root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    log_folder = os.path.join(root_directory, logs_folder)
    log_file = os.path.join(log_folder, log_file_name)
    print("log_file is {}".format(log_file))
    print("logs_folder is {}".format(logs_folder))
    logging.basicConfig(filename=log_file, level=logging.INFO, filemode='a', datefmt='%Y-%m-%d:%H:%M:%S',
                        format='%(threadName)s:%(thread)d:%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')

    return logging.getLogger(__name__)


logger = get_logger("UnifiedProxy.log")

# --- Load broker configuration from file ---
def load_broker_config():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "broker_config.json")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded broker configuration from {config_file}")
            return config.get("broker_api_end_points", {})
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {e}")
        return {}

broker_api_end_points = load_broker_config()

# --- Load user configuration from file ---
def load_user_config():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_config.json")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded user configuration from {config_file}")
            return config.get("users", [])
    except FileNotFoundError:
        logger.error(f"User configuration file not found: {config_file}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing user configuration file: {e}")
        return []

def save_user_config(users):
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_config.json")
    try:
        with open(config_file, 'w') as f:
            json.dump({"users": users}, f, indent=2)
            logger.info(f"Saved user configuration to {config_file}")
            return True
    except Exception as e:
        logger.error(f"Error saving user configuration: {e}")
        return False

user_configs = load_user_config()

# Track last request time for each user (for rate limiting)
user_last_request_time = {}


def get_broker_root_api(api_name):
    host = "https://xts.compositedge.com"
    baep = broker_api_end_points.get(api_name)

    if baep:
        host = baep["host"]
        # ws = baep["websocket"]
    logger.info("using host {} for api_name {}".format(host, api_name))
    # print("using ws {}".format(ws))
    return host


# --- API Endpoints (must be defined before catch-all route) ---
@app.get("/api/stats")
async def get_stats():
    """Return server statistics as JSON"""
    print(f"API Stats endpoint called. Current stats: {stats}")
    response_data = {
        "total_requests": stats["total_requests"],
        "by_broker": dict(stats["by_broker"]),
        "by_method": dict(stats["by_method"]),
        "by_action": dict(stats["by_action"]),
        "by_status": {str(k): v for k, v in stats["by_status"].items()},
        "start_time": stats["start_time"],
        "last_request_time": stats["last_request_time"],
        "last_request_received": stats["last_request_received"],
        "last_response_sent": stats["last_response_sent"],
        "avg_response_time_ms": round(stats["avg_response_time_ms"], 2),
        "min_response_time_ms": round(stats["min_response_time_ms"], 2) if stats["min_response_time_ms"] is not None else None,
        "max_response_time_ms": round(stats["max_response_time_ms"], 2) if stats["max_response_time_ms"] is not None else None,
        "errors": stats["errors"],
        "success": stats["success"],
        "uptime_seconds": (datetime.now() - datetime.fromisoformat(stats["start_time"])).total_seconds()
    }
    print(f"Returning response: {response_data}")
    return JSONResponse(content=response_data)

@app.post("/api/stats/reset")
async def reset_stats():
    """Reset all statistics"""
    stats["total_requests"] = 0
    stats["by_broker"].clear()
    stats["by_method"].clear()
    stats["by_action"].clear()
    stats["by_status"].clear()
    stats["start_time"] = datetime.now().isoformat()
    stats["last_request_time"] = None
    stats["last_request_received"] = None
    stats["last_response_sent"] = None
    stats["total_response_time_ms"] = 0
    stats["avg_response_time_ms"] = 0
    stats["min_response_time_ms"] = None
    stats["max_response_time_ms"] = None
    stats["errors"] = 0
    stats["success"] = 0
    return JSONResponse(content={"message": "Statistics reset successfully"})

@app.post("/api/config/reload")
async def reload_config():
    """Reload broker configuration from file"""
    global broker_api_end_points
    broker_api_end_points = load_broker_config()
    return JSONResponse(content={
        "message": "Configuration reloaded successfully",
        "brokers_count": len(broker_api_end_points)
    })

# --- User Configuration API Endpoints ---
@app.get("/api/users")
async def get_users():
    """Get all configured users"""
    return JSONResponse(content={"users": user_configs})

@app.post("/api/users")
async def add_user(request: Request):
    """Add a new user configuration"""
    try:
        data = await request.json()
        userid = data.get("userid")
        name = data.get("name")
        original_host_ip = data.get("original_host_ip")
        user_password = data.get("user_password")
        
        if not userid or not name or not original_host_ip or not user_password:
            raise HTTPException(status_code=400, detail="userid, name, original_host_ip, and user_password are required")
        
        # Check if user already exists
        for user in user_configs:
            if user["userid"] == userid:
                raise HTTPException(status_code=400, detail=f"User with userid {userid} already exists")
        
        new_user = {
            "userid": userid,
            "name": name,
            "original_host_ip": original_host_ip,
            "user_password": user_password,
            "added_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        user_configs.append(new_user)
        save_user_config(user_configs)
        
        logger.info(f"Added new user: {userid} - {name} at {original_host_ip}")
        return JSONResponse(content={"message": "User added successfully", "user": new_user})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{userid}")
async def delete_user(userid: str):
    """Delete a user configuration"""
    global user_configs
    user_configs = [u for u in user_configs if u["userid"] != userid]
    save_user_config(user_configs)
    logger.info(f"Deleted user: {userid}")
    return JSONResponse(content={"message": "User deleted successfully"})

@app.get("/api/users/{userid}/data")
async def get_user_data(userid: str):
    """Fetch user data from their original host"""
    user = next((u for u in user_configs if u["userid"] == userid), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Rate limiting: Check if user made a request in the last 60 seconds
    current_time = datetime.now()
    if userid in user_last_request_time:
        time_diff = (current_time - user_last_request_time[userid]).total_seconds()
        if time_diff < 30:
            remaining_time = int(30 - time_diff)
            raise HTTPException(
                status_code=429, 
                detail=f"Rate limit exceeded. Please wait {remaining_time} seconds before trying again."
            )
    
    # Update last request time
    user_last_request_time[userid] = current_time
    
    original_host = user["original_host_ip"]
    user_password = user.get("user_password", "")
    
    user_data = {
        "userid": userid,
        "name": user["name"],
        "original_host": original_host,
        "status": "offline",
        "data": None,
        "last_updated": datetime.now().isoformat()
    }
    
    try:
        print(f"Fetching data for user {userid} from host {original_host}")
        
        # Prepare request payload
        payload = {
            "trans_type": "QUERYUSER",
            "symbol": "BANKNIFTY",
            "trade_users": userid,
            "user_password": user_password
        }
        
        print(f"Sending request to https://{original_host}/tvUpdateConfigs with payload: {payload}")
        
        # Send request to tvUpdateConfigs endpoint
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            response = await client.post(
                f"https://{original_host}/tvUpdateConfigs",
                json=payload
            )
            
            if response.status_code == 200:
                user_data["status"] = "online"
                user_data["data"] = response.json()
                print(f"Successfully fetched data for user {userid} : {user_data.get('data')}")
            else:
                user_data["error"] = f"HTTP {response.status_code}: {response.text}"
                print(f"Failed to fetch data: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"Error fetching data for user {userid}: {e}")
        user_data["error"] = str(e)
        print(f"Exception while fetching data: {e}")
    
    return JSONResponse(content=user_data)

# --- Generic Proxy for XTS (must be defined AFTER specific API routes) ---
@app.api_route("/{broker}/{action:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def xts_proxy(broker: str, action: str, request: Request):
    # Skip proxy for internal API routes and common browser requests
    if broker in ["api", "favicon.ico"]:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Track request received time
    request_received_time = datetime.now()
    
    # Update statistics
    stats["total_requests"] += 1
    stats["by_broker"][broker] += 1
    stats["by_method"][request.method] += 1
    stats["by_action"][action] += 1
    stats["last_request_time"] = request_received_time.isoformat()
    stats["last_request_received"] = request_received_time.isoformat()
    
    try:
        # Log request headers
        logger.info(f"Received Request for broker {broker} query {request.query_params} "
                    f"action {action} headers: {request.headers} payload : {request.body()}")
        # Get broker host
        broker_host = get_broker_root_api(broker)
        target_url = f"{broker_host}/{action}"

        # Prepare request data
        method = request.method
        headers = dict(request.headers)
        # Remove host header to avoid conflicts
        headers.pop("host", None)

        # Query params
        params = dict(request.query_params)

        # Body (if any)
        body = await request.body()
        content = body if body else None
        logger.info(f"mannics content is {content}")

        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=params,
                content=content
            )
        
        # Track response sent time and calculate response time
        response_sent_time = datetime.now()
        response_time_ms = (response_sent_time - request_received_time).total_seconds() * 1000
        
        # Update statistics
        stats["by_status"][resp.status_code] += 1
        if 200 <= resp.status_code < 300:
            stats["success"] += 1
        else:
            stats["errors"] += 1
        
        # Update timing statistics
        stats["last_response_sent"] = response_sent_time.isoformat()
        stats["total_response_time_ms"] += response_time_ms
        stats["avg_response_time_ms"] = stats["total_response_time_ms"] / stats["total_requests"]
        
        # Update min/max response times
        if stats["min_response_time_ms"] is None or response_time_ms < stats["min_response_time_ms"]:
            stats["min_response_time_ms"] = response_time_ms
        if stats["max_response_time_ms"] is None or response_time_ms > stats["max_response_time_ms"]:
            stats["max_response_time_ms"] = response_time_ms
        
        logger.info(f"Send Response from {broker} for action {action}: Status {resp.status_code} Response Time: {response_time_ms:.2f}ms Res: {resp.json()} ")
        print(f"stats are {stats}")
        return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text

    except HTTPException as http_exc:
        stats["errors"] += 1
        logger.error(f"HTTP error during {action}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        stats["errors"] += 1
        logger.error(f"XTS error during {action}: {e} {traceback.print_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def read_root():
    # Build brokers list
    brokers_list = "<ul style='columns: 2; margin: 20px 0;'>"
    for broker_name in broker_api_end_points.keys():
        brokers_list += f"<li style='margin: 5px 0;'><strong>{broker_name}</strong>: {broker_api_end_points[broker_name]['host']}</li>"
    brokers_list += "</ul>"
    
    # Load HTML template
    html_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace("{BROKER_COUNT}", str(len(broker_api_end_points)))
        html_content = html_content.replace("{BROKERS_LIST}", brokers_list)
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<html><body><h1>Error: index.html not found</h1></body></html>", status_code=500)


# Entry point for running the proxy server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("FirststockClientProxy:app", host="0.0.0.0", port=9000, reload=True)
