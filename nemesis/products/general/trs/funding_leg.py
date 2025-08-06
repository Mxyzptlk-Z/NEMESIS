import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Union, List, Tuple

from ....utils.error import FinError
from ....utils.date import Date
from ....utils.day_count import DayCount, DayCountTypes
from ....utils.helpers import (
    format_table,
    label_to_string,
    check_argument_types,
)
from ....utils.global_types import SwapTypes
from ....utils.date_helper import get_year_fraction
from ....utils.fx_helper import get_trs_fx_spot


class FundingLeg(ABC):

    def __init__(
        self,
        start_dts: List[Date], 
        end_dts: List[Date], 
        payment_dts: List[Date], 
        leg_type: SwapTypes, 
        notionals: List[float], 
        dc_type: DayCountTypes 
    ):
                
        if not (len(notionals) == len(start_dts) == len(end_dts) == len(payment_dts)):
            raise FinError("Schedule info must match!")
        
        self.start_dts = start_dts
        self.end_dts = end_dts
        self.payment_dts = payment_dts
        self.leg_type = leg_type
        self.notionals = notionals
        self.dc_type = dc_type

    @abstractmethod
    def value(self) -> None:
        raise NotImplementedError("value method must be implemented")


class FixedFundingLeg(FundingLeg):

    def __init__(self, fixed_rate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_rate = fixed_rate
    
    def value(
            self,
            value_dt: Date,
            is_only_realized: bool = False,
            is_only_unsettled: bool = False,
            pv_only: bool = True
        ):
        
        leg_pv = 0.0
        # day_counter = DayCount(self.dc_type)

        self.payment_pvs = []
        self.cumulative_pvs = []

        for notional, start_dt, end_dt, payment_dt in zip(
            self.notionals, self.start_dts, self.end_dts, self.payment_dts):
            
            if start_dt <= value_dt and payment_dt > value_dt: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_dt >= value_dt:
                    continue
                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_dt < value_dt:
                    continue
                
                acr_end_dt = min(end_dt, value_dt)
                # acr_period = day_counter.year_frac(start_dt, acr_end_dt)[0]
                acr_period = get_year_fraction(self.dc_type, start_dt, acr_end_dt)

                payment_pv = notional * self.fixed_rate * acr_period
                leg_pv += payment_pv

                self.payment_pvs.append(payment_pv)
                self.cumulative_pvs.append(leg_pv)
            
            else:
                self.payment_pvs.append(0.0)
                self.cumulative_pvs.append(leg_pv)
        
        if pv_only:
            return leg_pv
        else:
            return leg_pv, self._cashflow_report_from_cached_values()

    ###########################################################################

    def _cashflow_report_from_cached_values(self):
        
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        
        df = pd.DataFrame()
        df["accrual_start_date"] = self.start_dts
        df["accrual_end_date"] = self.end_dts
        df["payment_date"] = self.payment_dts
        df["payment_pv"] = np.array(self.payment_pvs) * leg_type_sign
        df["leg"] = "TOTAL_RETURN_FUNDING"
        
        return df


class FloatFundingLeg(FundingLeg):

    def __init__(self, fixed_rate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_rate = fixed_rate
    
    def value(
            self,
            value_dt: Date,
            is_only_realized: bool = False,
            is_only_unsettled: bool = False,
            pv_only: bool = True
        ):
        
        leg_pv = 0.0
        day_counter = DayCount(self.dc_type)

        self.payment_pvs = []
        self.cumulative_pvs = []

        for notional, start_dt, end_dt, payment_dt in zip(
            self.notionals, self.start_dts, self.end_dts, self.payment_dts):
            
            if start_dt <= value_dt and payment_dt > value_dt: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_dt >= value_dt:
                    continue
                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_dt < value_dt:
                    continue
                
                acr_end_dt = min(end_dt, value_dt)
                acr_period = day_counter.year_frac(start_dt, acr_end_dt)[0]

                payment_pv = notional * self.fixed_rate * acr_period
                leg_pv += payment_pv

                self.payment_pvs.append(payment_pv)
                self.cumulative_pvs.append(leg_pv)
            
            else:
                self.payment_pvs.append(0.0)
                self.cumulative_pvs.append(leg_pv)
        
        if pv_only:
            return leg_pv
        else:
            return leg_pv, self._cashflow_report_from_cached_values()

    ###########################################################################

    def _cashflow_report_from_cached_values(self):
        
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        
        df = pd.DataFrame()
        df["accrual_start_date"] = self.start_dts
        df["accrual_end_date"] = self.end_dts
        df["payment_date"] = self.payment_dts
        df["payment_pv"] = np.array(self.payment_pvs) * leg_type_sign
        df["leg"] = "TOTAL_RETURN_FUNDING"
        
        return df

    ###########################################################################

class CrossBorderFixedFundingLeg(FixedFundingLeg):

    def __init__(
        self,
        fixed_rate: float,
        funding_ccy: str,
        settle_ccy: str,
        ccy_pair: str,
        fx_fixing_dts: List[Date], 
        fx_fixing: pd.Series = pd.Series(dtype=np.float64), 
        *args, **kwargs
    ):
        super().__init__(fixed_rate, *args, **kwargs)
        
        self.funding_ccy = funding_ccy.upper()
        self.settle_ccy = settle_ccy.upper()
        self.ccy_pair = ccy_pair.upper()
        self.fx_fixing_dts = fx_fixing_dts
        self.fx_fixing = fx_fixing
        
        if not (len(self.notionals) == len(self.fx_fixing_dts)):
            raise FinError("Schedule info of fx rate fixing must match!")

    ###########################################################################

    def value(
            self,
            value_dt: Date,
            fx_spot: float,
            is_only_realized: bool = False,
            is_only_unsettled: bool = False,
            pv_only: bool = True
        ):

        leg_pv = 0.0
        # day_counter = DayCount(self.dc_type)

        self.payment_pvs = []
        self.cumulative_pvs = []

        for notional, start_dt, end_dt, payment_dt, fx_fixing_dt in zip(
            self.notionals, self.start_dts, self.end_dts, self.payment_dts, self.fx_fixing_dts):
            
            if start_dt <= value_dt and payment_dt > value_dt: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_dt >= value_dt:
                    continue
                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_dt < value_dt:
                    continue
                
                acr_end_dt = min(end_dt, value_dt)
                # acr_period = day_counter.year_frac(start_dt, acr_end_dt)[0]
                acr_period = get_year_fraction(self.dc_type, start_dt, acr_end_dt)

                fx_rate = get_trs_fx_spot(self.funding_ccy, self.ccy_pair, value_dt, fx_fixing_dt, self.fx_fixing, fx_spot)

                payment_pv = notional * self.fixed_rate * acr_period * fx_rate
                leg_pv += payment_pv

                self.payment_pvs.append(payment_pv)
                self.cumulative_pvs.append(leg_pv)
            
            else:
                self.payment_pvs.append(0.0)
                self.cumulative_pvs.append(leg_pv)
        
        if pv_only:
            return leg_pv
        else:
            return leg_pv, self._cashflow_report_from_cached_values()

    ###########################################################################

    def _cashflow_report_from_cached_values(self):
        
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        
        df = pd.DataFrame()
        df["accrual_start_date"] = self.start_dts
        df["accrual_end_date"] = self.end_dts
        df["payment_date"] = self.payment_dts
        df["payment_pv"] = np.array(self.payment_pvs) * leg_type_sign
        df["leg"] = "TOTAL_RETURN_FUNDING"
        
        return df


__all__ = ["FixedFundingLeg", "FloatFundingLeg", "CrossBorderFixedFundingLeg"]