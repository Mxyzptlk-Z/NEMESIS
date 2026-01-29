from abc import ABCMeta, abstractmethod
import pandas as pd

from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCountTypes

from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes


###############################################################################


class VolSurface:

    __metaclass__ = ABCMeta

    ###########################################################################

    def __init__(
        self,
        value_dt: Date,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
    ):
        self.value_dt = value_dt

        self.cal_type = cal_type
        self.dc_type = dc_type

        self._calendar = Calendar(cal_type)
        self._day_count = DayCount(dc_type)

    ###########################################################################

    @abstractmethod
    def _build_vol_data(self) -> pd.DataFrame:
        raise NotImplementedError("Should implement `_build_vol_data`")

    ###########################################################################

    @abstractmethod
    def interp_vol(self, expiry_dt: Date, strike: float) -> float:
        """
        Interpolate volatility for a given expiry and strike.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        strike : float
            Option strike price

        Returns
        -------
        float
            Interpolated volatility
        """
        raise NotImplementedError("Should implement `interp_vol`")


###############################################################################
