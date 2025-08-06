import numpy as np
import pandas as pd
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
from ....utils.fx_helper import get_trs_fx_spot

###############################################################################


class AssetLeg:

    def __init__(
        self,
        start_dt: Date,
        expiry_dt: Date,
        reset_dts: List[Date],
        payment_dts: List[Date],
        leg_type: SwapTypes,
        quantity: float,
        initial_asset_price: float,
        is_fixed_qty: bool = True,
        spread: float = 0.0,
        spread_dc_type: DayCountTypes = DayCountTypes.ACT_365F,
        spread_notional_reset: bool = True,
        asset_prices: pd.Series = pd.Series(dtype=np.float64),
    ):
        
        # check_argument_types(self.__init__, locals())
        
        self.start_dt = start_dt
        self.expiry_dt = expiry_dt
        self.reset_dts = reset_dts
        self.payment_dts = payment_dts
        self.leg_type = leg_type
        self.quantity = quantity
        self.initial_asset_price = initial_asset_price
        self.is_fixed_qty = is_fixed_qty 
        self.spread = spread
        self.spread_dc_type = spread_dc_type
        self.spread_notional_reset = spread_notional_reset
        self.asset_prices = asset_prices

        self._validate_input()

    ###########################################################################

    def _validate_input(self):
        if not self.reset_dts[-1] == self.expiry_dt:
            raise FinError("Last reset date must be expiry date!")
        
        if not len(self.reset_dts) == len(self.payment_dts):
            raise FinError("Reset dates and payment dates must match!")

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        latest_asset_price: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True,
    ):
        
        leg_pv = 0.0
        num_payments = len(self.payment_dts)

        self.payment_pvs = []
        self.cumulative_pvs = []
        
        for i_pmnt in range(num_payments):

            payment_dt = self.payment_dts[i_pmnt]
            reset_dt = self.reset_dts[i_pmnt]
            last_reset_dt = self.start_dt if i_pmnt == 0 else self.reset_dts[i_pmnt - 1]
            
            if payment_dt < reset_dt:
                raise FinError("Payment date should be later than reset date!")
                
            if payment_dt > value_dt and last_reset_dt <= value_dt:
                # if is_only_realized and reset_date > today:
                if is_only_realized and reset_dt >= value_dt:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and reset_dt < value_dt:
                    continue
                
                last_asset_price, current_asset_price = self._get_asset_price(
                    i_pmnt, last_reset_dt, reset_dt, value_dt, self.initial_asset_price, 
                    latest_asset_price, self.asset_prices)
                
                if self.is_fixed_qty:
                    qty_i = self.quantity
                else:
                    qty_i = self.quantity * self.initial_asset_price / last_asset_price
                
                asset_payment = qty_i * (current_asset_price - last_asset_price)
                
                if self.spread_notional_reset:
                    spread_notional = self.quantity * last_asset_price
                else:
                    spread_notional = self.quantity * self.initial_asset_price
                
                spread_day_counter = DayCount(self.spread_dc_type)
                spread_peirod = spread_day_counter.year_frac(last_reset_dt, min(value_dt, reset_dt))[0]
                spread_payment = spread_notional * self.spread * spread_peirod
                
                payment_pv = asset_payment + spread_payment
                leg_pv += payment_pv

                self.payment_pvs.append(payment_pv)
                self.cumulative_pvs.append(leg_pv)
            
            else:
                self.payment_pvs.append(0.0)
                self.cumulative_pvs.append(leg_pv)
        
        if self.leg_type == SwapTypes.PAY:
            leg_pv = leg_pv * (-1.0)

        if pv_only:
            return leg_pv
        else:
            return leg_pv, self._cashflow_report_from_cached_values()

    ###########################################################################

    def _get_asset_price(
            self, n_payment, last_reset_dt, reset_dt, value_dt, 
            init_price, latest_price, ref_prices
        ) -> Tuple[float]:
        
        if n_payment == 0:
            last_asset_price = init_price
        else:
            try:
                last_asset_price = ref_prices[last_reset_dt]
            except:
                print("Warning: last asset price not found, use latest price instead")
                last_asset_price = latest_price
        
        if value_dt >= reset_dt:
            try:
                current_asset_price = ref_prices[reset_dt]
            except:
                print("Warning: current asset price not found, use latest price instead")
                current_asset_price = latest_price
        else:
            current_asset_price = latest_price
        
        return last_asset_price, current_asset_price

    ###########################################################################

    def _cashflow_report_from_cached_values(self):
        
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        accrue_schedule = [self.start_dt] + self.reset_dts
        
        df = pd.DataFrame()
        df["accrual_start_date"] = accrue_schedule[:-1]
        df["accrual_end_date"] = accrue_schedule[1:]
        df["payment_date"] = self.payment_dts
        df["asset_price"] = self.asset_prices
        df["payment_pv"] = np.array(self.payment_pvs) * leg_type_sign
        df["leg"] = "TOTAL_RETURN_ASSET"
        
        return df

    ###########################################################################

    # def print_valuation(self):
    #     """打印估值详情"""
        
    #     print("起始日期:", self.effective_dt)
    #     print("到期日期:", self.maturity_dt)
    #     print("初始资产价格:", self.initial_asset_price)
    #     print("股息率 (%):", self.dividend_yield * 100)
    #     print("付款频率:", str(self.freq_type))
    #     print("日期计算:", str(self.dc_type))

    #     if len(self.total_payments) == 0:
    #         print("付款未计算。")
    #         return

    #     header = [
    #         "付款序号",
    #         "付款日期",
    #         "名义本金", 
    #         "资产价格",
    #         "价格回报(%)",
    #         "股息支付",
    #         "总支付",
    #         "贴现因子",
    #         "现值",
    #         "累计现值",
    #     ]

    #     rows = []
    #     num_flows = len(self.payment_dts)
    #     for i_flow in range(num_flows):
    #         rows.append([
    #             i_flow + 1,
    #             self.payment_dts[i_flow],
    #             round(self.notional, 0),
    #             round(self.asset_prices[i_flow], 2),
    #             round(self.total_returns[i_flow] * 100.0, 4),
    #             round(self.dividend_payments[i_flow], 2),
    #             round(self.total_payments[i_flow], 2),
    #             round(self.payment_dfs[i_flow], 4),
    #             round(self.payment_pvs[i_flow], 2),
    #             round(self.cumulative_pvs[i_flow], 2),
    #         ])

    #     table = format_table(header, rows)
    #     print("\n付款估值详情:")
    #     print(table)

    ###########################################################################

    def __repr__(self):

        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("START DATE", self.start_dt)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("SPREAD", self.spread)
        s += label_to_string("QUANTITY", self.quantity)
        s += label_to_string("LEG TYPE", self.leg_type)

        return s


class CrossBorderAssetLeg(AssetLeg):

    def __init__(
        self,
        asset_ccy: str,
        settle_ccy: str,
        ccy_pair: str,
        start_dt: Date,
        expiry_dt: Date,
        reset_dts: List[Date],
        payment_dts: List[Date],
        fx_fixing_dts: List[Date],
        leg_type: SwapTypes,
        quantity: float,
        initial_asset_price: float,
        is_fixed_qty: bool = True,
        spread: float = 0.0,
        spread_dc_type: DayCountTypes = DayCountTypes.ACT_365F,
        spread_notional_reset: bool = True,
        asset_prices: pd.Series = pd.Series(dtype=np.float64),
        fx_fixing: pd.Series = pd.Series(dtype=np.float64)
    ):
        super().__init__(
            start_dt, expiry_dt, reset_dts, payment_dts, leg_type, quantity, initial_asset_price,
            is_fixed_qty, spread, spread_dc_type, spread_notional_reset, asset_prices
        )
        
        self.asset_ccy = asset_ccy
        self.settle_ccy = settle_ccy
        self.ccy_pair = ccy_pair
        self.fx_fixing_dts = fx_fixing_dts
        self.fx_fixing = fx_fixing

        self._validate_crossborder_input()

    ###########################################################################

    def _validate_crossborder_input(self):
        if not (len(self.reset_dts) == len(self.fx_fixing_dts)):
            raise FinError("Reset dates and fx rate fixing dates must match!")

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        latest_asset_price: float,
        fx_spot: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True,
    ):
        
        leg_pv = 0.0
        num_payments = len(self.payment_dts)

        self.payment_pvs = []
        self.cumulative_pvs = []
        
        for i_pmnt in range(num_payments):

            payment_dt = self.payment_dts[i_pmnt]
            reset_dt = self.reset_dts[i_pmnt]
            last_reset_dt = self.start_dt if i_pmnt == 0 else self.reset_dts[i_pmnt - 1]
            fx_fixing_dt = self.fx_fixing_dts[i_pmnt]
            
            if payment_dt < reset_dt:
                raise FinError("Payment date should be later than reset date!")
            if payment_dt < fx_fixing_dt:
                raise FinError("Payment date should be later than fx rate fixing date!")
                
            if payment_dt > value_dt and last_reset_dt <= value_dt:
                # if is_only_realized and reset_date > today:
                if is_only_realized and reset_dt >= value_dt:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and reset_dt < value_dt:
                    continue
                
                last_asset_price, current_asset_price = self._get_asset_price(
                    i_pmnt, last_reset_dt, reset_dt, value_dt, self.initial_asset_price, 
                    latest_asset_price, self.asset_prices)
                
                if self.is_fixed_qty:
                    qty_i = self.quantity
                else:
                    qty_i = self.quantity * self.initial_asset_price / last_asset_price
                
                asset_payment = qty_i * (current_asset_price - last_asset_price)
                
                if self.spread_notional_reset:
                    spread_notional = self.quantity * last_asset_price
                else:
                    spread_notional = self.quantity * self.initial_asset_price
                
                spread_day_counter = DayCount(self.spread_dc_type)
                spread_peirod = spread_day_counter.year_frac(last_reset_dt, min(value_dt, reset_dt))[0]
                spread_payment = spread_notional * self.spread * spread_peirod

                fx_rate = get_trs_fx_spot(self.asset_ccy, self.ccy_pair, value_dt, fx_fixing_dt, self.fx_fixing, fx_spot)
                
                payment_pv = (asset_payment + spread_payment) * fx_rate
                leg_pv += payment_pv

                self.payment_pvs.append(payment_pv)
                self.cumulative_pvs.append(leg_pv)
            
            else:
                self.payment_pvs.append(0.0)
                self.cumulative_pvs.append(leg_pv)
        
        if self.leg_type == SwapTypes.PAY:
            leg_pv = leg_pv * (-1.0)

        if pv_only:
            return leg_pv
        else:
            return leg_pv, self._cashflow_report_from_cached_values()

    ###########################################################################

    def _cashflow_report_from_cached_values(self):
        
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        accrue_schedule = [self.start_dt] + self.reset_dts
        
        df = pd.DataFrame()
        df["accrual_start_date"] = accrue_schedule[:-1]
        df["accrual_end_date"] = accrue_schedule[1:]
        df["payment_date"] = self.payment_dts
        df["asset_price"] = self.asset_prices
        df["payment_pv"] = np.array(self.payment_pvs) * leg_type_sign
        df["leg"] = "TOTAL_RETURN_ASSET"
        
        return df

    ###########################################################################