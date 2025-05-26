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