"""
ATM Strike Selector
Dynamically calculates ATM strike and fetches option instruments
"""

import requests
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ATMSelector:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        self.current_strike = None
        self.ce_instrument_key = None
        self.pe_instrument_key = None
        self.expiry_date = None
    
    def get_nifty_spot(self):
        """Get current NIFTY spot price"""
        try:
            import urllib.parse
            instrument_key = urllib.parse.quote("NSE_INDEX|Nifty 50", safe='')
            url = f"{self.base_url}/market-quote/quotes?instrument_key={instrument_key}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ltp = data['data']['NSE_INDEX:Nifty 50']['last_price']
                logger.info(f"✅ NIFTY Spot: {ltp}")
                return ltp
            else:
                logger.error(f"❌ Failed to get NIFTY spot: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Error fetching NIFTY spot: {e}")
            return None
    
    def calculate_atm_strike(self, spot_price):
        """Round spot to nearest 50"""
        atm = int(round(spot_price / 50) * 50)
        logger.info(f"🎯 Spot: {spot_price} → ATM: {atm}")
        return atm
    
    def get_nearest_expiry(self):
        """Get nearest weekly/monthly expiry for NIFTY options"""
        try:
            import urllib.parse
            index_key = urllib.parse.quote("NSE_INDEX|Nifty 50", safe='')
            url = f"{self.base_url}/option/contract?instrument_key={index_key}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expiries = data['data']
                
                # Get unique expiry dates
                expiry_dates = sorted(list(set([contract['expiry'] for contract in expiries])))
                
                if expiry_dates:
                    nearest_expiry = expiry_dates[0]
                    logger.info(f"📅 Nearest Expiry: {nearest_expiry}")
                    return nearest_expiry
                else:
                    logger.error("❌ No expiries found!")
                    return None
            else:
                logger.error(f"❌ Failed to fetch expiries: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Error fetching expiries: {e}")
            return None
    
    def get_atm_instruments(self, strike, expiry_date):
        """Get CE and PE instrument keys for ATM strike"""
        try:
            import urllib.parse
            index_key = urllib.parse.quote("NSE_INDEX|Nifty 50", safe='')
            url = f"{self.base_url}/option/contract?instrument_key={index_key}&expiry_date={expiry_date}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                contracts = data['data']
                
                ce_key = None
                pe_key = None
                
                for contract in contracts:
                    if contract['strike_price'] == strike:
                        if contract['instrument_type'] == 'CE':
                            ce_key = contract['instrument_key']
                        elif contract['instrument_type'] == 'PE':
                            pe_key = contract['instrument_key']
                
                if ce_key and pe_key:
                    logger.info(f"✅ ATM Instruments Found!")
                    logger.info(f"   CE: {ce_key}")
                    logger.info(f"   PE: {pe_key}")
                    return ce_key, pe_key
                else:
                    logger.error(f"❌ Missing ATM contracts! CE: {bool(ce_key)} PE: {bool(pe_key)}")
                    return None, None
            else:
                logger.error(f"❌ Failed to fetch contracts: {response.text}")
                return None, None
                
        except Exception as e:
            logger.error(f"💥 Error fetching ATM instruments: {e}")
            return None, None
    
    def initialize_atm(self):
        """Initialize ATM strike and instruments"""
        logger.info("="*70)
        logger.info("🎯 INITIALIZING ATM STRIKE SELECTOR")
        logger.info("="*70)
        
        # Get NIFTY spot
        spot = self.get_nifty_spot()
        if not spot:
            return False
        
        # Calculate ATM
        self.current_strike = self.calculate_atm_strike(spot)
        
        # Get nearest expiry
        self.expiry_date = self.get_nearest_expiry()
        if not self.expiry_date:
            return False
        
        # Get ATM instruments
        self.ce_instrument_key, self.pe_instrument_key = self.get_atm_instruments(
            self.current_strike, 
            self.expiry_date
        )
        
        if self.ce_instrument_key and self.pe_instrument_key:
            logger.info("✅ ATM Selection Complete!")
            logger.info(f"   Strike: {self.current_strike}")
            logger.info(f"   Expiry: {self.expiry_date}")
            return True
        else:
            logger.error("❌ ATM Selection Failed!")
            return False
    
        def get_current_config(self):
            """Return current ATM configuration"""
            return {
                'strike': self.current_strike,
                'expiry': self.expiry_date,
                'ce_key': self.ce_instrument_key,
                'pe_key': self.pe_instrument_key
            }
    
        def get_atm_keys(self, spot_price):
            """
            Get ATM strike and keys for a given spot price.
            Returns: (atm_strike, ce_key, pe_key)
            """
            if not spot_price:
                spot_price = self.get_nifty_spot()
            
            if not spot_price:
                return None, None, None
                
            atm_strike = self.calculate_atm_strike(spot_price)
            expiry_date = self.get_nearest_expiry()
            
            if not expiry_date:
                return atm_strike, None, None
                
            ce_key, pe_key = self.get_atm_instruments(atm_strike, expiry_date)
            
            return atm_strike, ce_key, pe_key    
    def get_atm_keys(self, spot_price=None):
        """
        Get ATM strike and instrument keys for a given spot price.
        Returns: (atm_strike, ce_key, pe_key)
        """ 
        if spot_price is None:
            spot_price = self.get_nifty_spot()
            if spot_price is None:
                logger.error("❌ Could not fetch NIFTY spot price.")
                return None, None, None

        atm_strike = self.calculate_atm_strike(spot_price)
        
        expiry_date = self.get_nearest_expiry()
        if not expiry_date:
            return atm_strike, None, None
            
        ce_key, pe_key = self.get_atm_instruments(atm_strike, expiry_date)
        
        return atm_strike, ce_key, pe_key