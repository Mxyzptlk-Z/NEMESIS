from abc import ABCMeta, abstractmethod
import pandas as pd

from ...market.curves.interpolator import InterpTypes
from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCountTypes

from .discount_curve import DiscountCurve


###############################################################################


class ForwardCurve(DiscountCurve):
    """"""

    __metaclass__ = ABCMeta

    ###########################################################################

    def __init__(
        self,
        value_dt: Date,
        spot_rate: float,
        fwd_data: pd.DataFrame,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
        interp_type: InterpTypes
    ):
        self.value_dt = value_dt
        self.spot_rate = spot_rate
        self.fwd_data = fwd_data.copy()

        self.cal_type = cal_type
        self.dc_type = dc_type

        self._interp_type = interp_type
        self._interpolator = None

    ###########################################################################

    @abstractmethod
    def _build_curve(self):
        raise NotImplementedError("Should implement `_build_curve`")

    ###########################################################################

    @abstractmethod
    def get_forward(self, dt: Date, dc_type: DayCountTypes):
        raise NotImplementedError("Should implement `get_forward`")


###############################################################################