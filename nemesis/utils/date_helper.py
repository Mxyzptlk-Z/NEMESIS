from .date import Date
from .day_count import DayCount, DayCountTypes

def get_year_fraction(
        dc_type: DayCountTypes,
        start: Date,
        end: Date,
        day_stub: str = "IncludeFirstExcludeEnd"
    ):
    
    if dc_type == None:
        return 1.0
    else:
        if dc_type in [
            DayCountTypes.THIRTY_360_BOND, 
            DayCountTypes.THIRTY_E_360,
            DayCountTypes.THIRTY_E_360_ISDA,
            DayCountTypes.THIRTY_E_PLUS_360
        ]:
            pass
        else: 
            if day_stub == "ExcludeFirstExcludeEnd":
                end = end.add_days(-1)
            elif day_stub == "IncludeFirstIncludeEnd":
                end = end.add_days(1)
            else:
                pass
        day_counter = DayCount(dc_type)
        return day_counter.year_frac(start, end)[0]
