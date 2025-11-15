from Dhan_Tradehull import Tradehull

CLIENT_ID = "1108149450"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU3MDY4OTY0LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwODE0OTQ1MCJ9.xMPN_78BpWsJixx4G9qN4mWOV__NtzODYJE_Sb-gkF5uz9RucPImiWhItHKyU53Jf3AA0kxGmF-0DS6Qt0vU9A"

tsl = Tradehull(CLIENT_ID, ACCESS_TOKEN)

print("[INFO] Testing balance fetch...")
print(tsl.get_balance())

print("[INFO] Testing LTP fetch...")
print(tsl.get_ltp_data(names=['NIFTY']))
