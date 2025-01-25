import pandas as pd
import numpy as np



def get_float(x):
    try:
        return float(x)
    except:
        return x
    


def get_traces(trade_json):
    if 'traces' in trade_json.keys() and (not trade_json['traces'] == []):
        traces = pd.DataFrame(trade_json['traces'])
        traces.loc[:, 'type'] = [x.split('.')[-1] for x in list(traces.loc[:, 'type'])]
        traces['date'] = [x[:10] for x in list(traces.loc[:, 'effectiveTimestamp'])]
        traces.sort_values(by=['date', 'auditTimestamp'], inplace=True)
        traces.drop_duplicates(subset=['type', 'name', 'date'], keep='last', inplace=True)
        traces = traces.loc[:, ['type', 'value', 'name', 'date']]
        traces['value'] = traces['value'].apply(get_float)
    else:
        traces = pd.DataFrame(columns=['type', 'value', 'name', 'date'])
    
    return traces
    


def average_sigma(obs_dates, strike, vol_surf):
    if len(obs_dates) == 0:
        return None
    else:
        sigmas = []
        for obs_date in obs_dates:
            sigmas.append(vol_surf.interp_vol(obs_date, strike))
        return np.mean(np.array(sigmas))
    
    

# def singleton(cls, *args, **kw):
#      instances = {}
#      def _singleton(*args, **kw):
#         if cls not in instances:
#              instances[cls] = cls(*args, **kw)
#         return instances[cls]
#      return _singleton