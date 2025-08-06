import pandas as pd
from .date import Date


def fx_ccy_trans(value, orig_ccy, fx_rate, fx_pair='None', vague_match_cny_cnh=False):
    if fx_pair == 'None' or fx_pair == 'NONE':
        return value
    else:
        # support CNYCNH or CNHCNY pair
        if not(fx_pair == 'CNYCNH' or fx_pair == 'CNHCNY') and vague_match_cny_cnh:
            orig_ccy = orig_ccy.replace('CNH', 'CNY')
            fx_pair = fx_pair[:3].replace('CNH', 'CNY') + fx_pair[3:].replace('CNH', 'CNY')
            
        if orig_ccy == fx_pair[:3]:
            return value * fx_rate
        else:
            return value / fx_rate

def get_trs_fx_spot(
        asset_ccy: str, 
        ccy_pair: str, 
        value_dt: Date, 
        fx_fixing_dt: Date, 
        fx_fixing: pd.Series,
        fx_spot: float
    ):
    if fx_fixing_dt <= value_dt:
        try:
            fx_spot = fx_fixing.loc[fx_fixing_dt]
        except:
            pass
    return fx_ccy_trans(1, asset_ccy, fx_spot, ccy_pair, True)