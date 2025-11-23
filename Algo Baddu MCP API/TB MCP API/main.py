# backend/main.py
#print("HELLO BADDU:D")
from fastapi import FastAPI
from fyers_apiv3 import fyersModel
from fastapi.middleware.cors import CORSMiddleware

# 🎯 Fyers setup
access_token = "your_access_token_here"
client_id = "1NB0WIJFOT-100"

fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

# 🚀 FastAPI app
app = FastAPI()

# (Optional) Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "🚀 MCP FastAPI backend is live!"}

@app.get("/profile")
def get_profile():
    return fyers.get_profile()

@app.get("/quote")
def get_market_quote():
    return fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})

# 🧠 GitHub Copilot Prompt:
# Add a FastAPI route /candles in my main.py that reads candle data from a local file named "fetched_candles.json" and returns it as JSON.
# If the file doesn't exist, return a 404 error with message "Candle data not found."
# If there's an error while reading or parsing the JSON, return a 500 error with the exception message
# Assume the file is in the same directory as main.py
# Use JSONResponse from FastAPI for responses

from fastapi.responses import JSONResponse
import os
import json

@app.get("/candles")
def get_candles():
    file_path = os.path.join(os.path.dirname(__file__), "fetched_candles.json")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Candle data not found."})
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return JSONResponse(content={"candles": data})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
