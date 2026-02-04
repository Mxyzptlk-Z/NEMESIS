import copy
import pandas as pd

from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCountTypes

from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes

from .vol_surface import VolSurface


class ConstantVolSurface(VolSurface):

    def __init__(
        self,
        value_dt: Date,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
        sigma: str
    ):
        super().__init__(value_dt, cal_type, dc_type)
        self.sigma = sigma

    def _build_vol_data(self) -> pd.DataFrame:
        pass


    def interp_vol(self, expiry_dt: Date, strike: float) -> float:
        return self.sigma + self._vol_bump


    def bump_volatility(self, bump, inplace=False):
        if inplace:
            self._vol_bump += bump
            return self
        else:
            bumped_surface = copy.copy(self)
            bumped_surface._vol_bump += bump
            return bumped_surface
