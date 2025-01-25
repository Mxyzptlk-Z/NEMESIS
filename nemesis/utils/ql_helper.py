import QuantLib as ql
from .date import Date
from typing import Union
    
def ql_date_to_date(ql_date: Union[ql.Date, list]):
    """Convert a QuantLib Date to a Financepy Date."""

    if isinstance(ql_date, ql.Date):
        return Date(ql_date.dayOfMonth(), ql_date.month(), ql_date.year())

    elif isinstance(ql_date, list):
        return [Date(dt.dayOfMonth(), dt.month(), dt.year()) for dt in ql_date]
