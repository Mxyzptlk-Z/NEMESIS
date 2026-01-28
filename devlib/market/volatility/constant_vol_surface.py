import QuantLib as ql
import numpy as np
import math



class ConstantVolSurface:
    def __init__(self, today, sigma):
        self.today = today
        self.sigma = sigma
        
    
    def interp_vol(self, expiry=None, strike=None):
        return self.sigma
    

    def vol_tweak(self, tweak):
        sigma_tweak = self.sigma + tweak
        return ConstantVolSurface(self.today, sigma_tweak)
        

