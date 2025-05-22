from typing import Union

from ...utils.date import Date
from ...utils.error import FinError
from ...utils.calendar import Calendar
from ...utils.calendar import CalendarTypes
from ...utils.calendar import BusDayAdjustTypes
from ...utils.day_count import DayCount
from ...utils.day_count import DayCountTypes
from ...market.curves.discount_curve import DiscountCurve
from ...utils.helpers import label_to_string, check_argument_types


###############################################################################


class FXForward:

    def __init__(
        self,
        settle_dt: Date,
        maturity_dt_or_tenor: Union[Date, str],
        spot_rate: float,
        spread: float,
        dc_type: DayCountTypes,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.MODIFIED_FOLLOWING,
    ):
        """Create a Libor deposit object which takes the start date when
        the amount of notional is borrowed, a maturity date or a tenor and the
        deposit rate. If a tenor is used then this is added to the start
        date and the calendar and business day adjustment method are applied if
        the maturity date fall on a holiday. Note that in order to calculate
        the start date you add the spot business days to the trade date
        which usually today."""

        check_argument_types(self.__init__, locals())

        self.cal_type = cal_type        
        self.bd_type = bd_type

        if type(maturity_dt_or_tenor) is Date:
            maturity_dt = maturity_dt_or_tenor
        else:
            maturity_dt = settle_dt.add_tenor(maturity_dt_or_tenor)

        calendar = Calendar(cal_type)
        maturity_dt = calendar.adjust(maturity_dt, self.bd_type)

        if settle_dt > maturity_dt:
            raise FinError("Start date cannot be after maturity date")

        self.settle_dt = settle_dt
        self.maturity_dt = maturity_dt
        self.spot_rate = spot_rate
        self.spread = spread
        self.dc_type = dc_type
        self.fwd_rate = self._fwd_rate()

    ###########################################################################

    def _fwd_rate(self):
        fwd_rate = self.spot_rate + self.spread / 10000
        return fwd_rate 