import logging
import numpy as np
import pandas as pd
from typing import Union, List, Dict

from ....utils.error import FinError
from ....utils.date import Date
from ....utils.day_count import DayCountTypes
from ....utils.frequency import FrequencyTypes
from ....utils.calendar import CalendarTypes, DateGenRuleTypes
from ....utils.calendar import Calendar, BusDayAdjustTypes
from ....utils.helpers import check_argument_types, label_to_string
from ....utils.math import ONE_MILLION
from ....utils.global_types import SwapTypes
from ....market.curves.discount_curve import DiscountCurve

from .asset_leg import AssetLeg, CrossBorderAssetLeg
from .funding_leg import FundingLeg, FixedFundingLeg, FloatFundingLeg, CrossBorderFixedFundingLeg

logger = logging.getLogger(__name__)

###############################################################################


class TotalReturnSwap:

    def __init__(
        self,
        start_dt: Date,
        expiry_dt: Date,
        reset_dts: List[Date],
        payment_dts: List[Date],
        asset_leg_type: SwapTypes,
        quantity: float,
        initial_asset_price: float,
        is_fixed_qty: bool = True,
        spread: float = 0.0,
        spread_dc_type: DayCountTypes = DayCountTypes.ACT_365F,
        spread_notional_reset: bool = True,
        asset_prices: pd.Series = pd.Series(dtype=np.float64),
        funding_legs: Dict[str, FundingLeg] = {}
    ):
        
        # check_argument_types(self.__init__, locals())

        self.start_dt = start_dt
        self.expiry_dt = expiry_dt
        self.reset_dts = reset_dts
        self.payment_dts = payment_dts
        self.asset_leg_type = asset_leg_type
        self.quantity = quantity
        self.initial_asset_price = initial_asset_price
        self.is_fixed_qty = is_fixed_qty 
        self.spread = spread
        self.spread_dc_type = spread_dc_type
        self.spread_notional_reset = spread_notional_reset
        self.asset_prices = asset_prices
        self.funding_legs = funding_legs

        if start_dt > expiry_dt:
            raise FinError("Start date after expiry date")

        self.asset_leg = AssetLeg(
            start_dt,
            expiry_dt,
            reset_dts,
            payment_dts,
            asset_leg_type,
            quantity,
            initial_asset_price,
            is_fixed_qty,
            spread,
            spread_dc_type,
            spread_notional_reset,
            asset_prices
        )

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        latest_asset_price: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        **kwargs
    ):

        asset_leg_pv = self._asset_leg_value(
            value_dt, latest_asset_price, is_only_realized, is_only_unsettled, pv_only=True)
        
        # funding leg is optional
        fixings_dict = kwargs.get("fixings_dict", {})
        funding_leg_pvs = self._funding_legs_value(value_dt, fixings_dict, is_only_realized, is_only_unsettled, pv_only=True)
        funding_leg_pv = sum(funding_leg_pvs.values())

        total_value = asset_leg_pv + funding_leg_pv
        return total_value

    ###########################################################################

    def _asset_leg_value(
        self, 
        value_dt: Date,
        latest_asset_price: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True
    ):
        asset_leg_pv = self.asset_leg.value(
            value_dt, latest_asset_price,
            is_only_realized, is_only_unsettled, pv_only
        )
        return asset_leg_pv

    ###########################################################################

    def _funding_legs_value(
        self,
        value_dt: Date,
        fixings_dict: Dict[str, pd.Series] = {},
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True,
    ):
        self.funding_leg_pvs = {}

        if self.funding_legs:
            for key, funding_leg in self.funding_legs.items():
                if isinstance(funding_leg, FixedFundingLeg):
                    leg_pv = funding_leg.value(value_dt, is_only_realized, is_only_unsettled, pv_only)
                elif isinstance(funding_leg, FloatFundingLeg):
                    fixings = fixings_dict.get(key, {})
                    if not fixings:
                        raise FinError(f"fixing data not provided for {key}")
                    leg_pv = funding_leg.value(value_dt, fixings, is_only_realized, is_only_unsettled, pv_only)
                else:
                    raise FinError(f'Unsupported funding leg type: {type(funding_leg)}!')
                
                self.funding_leg_pvs[key] = leg_pv
        else:
            logger.info("There's no funding leg for this TRS")
        
        return self.funding_leg_pvs

    ###########################################################################

    def valuation_details(
        self,
        value_dt: Date,
        discount_curve: DiscountCurve,
        index_curve: DiscountCurve,
        current_asset_price: float,
        future_asset_prices: list = None,
        first_fixing_rate: float = None,
    ):
        """详细估值信息
        
        Returns:
        --------
        dict
            包含详细估值信息的字典
        """
        
        # 获取详细现金流
        total_value, cashflow_report = self.value(
            value_dt, discount_curve, index_curve,
            current_asset_price, future_asset_prices,
            first_fixing_rate, pv_only=False
        )
        
        # 分别计算各腿价值
        tr_leg_value = self.total_return_leg.value(
            value_dt, discount_curve, current_asset_price, future_asset_prices
        )
        
        float_leg_value = self.float_leg.value(
            value_dt, index_curve, discount_curve, first_fixing_rate
        )
        
        details = {
            "类型": type(self).__name__,
            "起始日期": self.effective_dt,
            "到期日期": self.maturity_dt,
            "名义本金": self.notional,
            "初始资产价格": self.initial_asset_price,
            "当前资产价格": current_asset_price,
            "股息率": self.dividend_yield,
            "融资利差": self.funding_spread,
            "总回报腿类型": self.total_return_leg.leg_type.name,
            "总回报腿价值": tr_leg_value,
            "浮动腿价值": float_leg_value,
            "互换总价值": total_value,
            "现金流明细": cashflow_report,
        }
        
        return details

    ###########################################################################

    def print_valuation(self):
        """打印估值概要"""
        
        print("=== 总回报互换概要 ===")
        print(f"起始日期: {self.effective_dt}")
        print(f"到期日期: {self.maturity_dt}")
        print(f"名义本金: {self.notional:,.0f}")
        print(f"初始资产价格: {self.initial_asset_price:.2f}")
        print(f"股息率: {self.dividend_yield*100:.2f}%")
        print(f"融资利差: {self.funding_spread*10000:.1f}bp")
        print(f"总回报腿类型: {self.total_return_leg.leg_type.name}")
        
        print("\n=== 总回报腿详情 ===")
        self.total_return_leg.print_valuation()
        
        print("\n=== 浮动利率腿详情 ===")
        self.float_leg.print_valuation()

    ###########################################################################

    def __repr__(self):
        s = label_to_string("对象类型", type(self).__name__)
        s += label_to_string("起始日期", self.effective_dt)
        s += label_to_string("到期日期", self.maturity_dt)
        s += label_to_string("名义本金", self.notional)
        s += label_to_string("初始资产价格", self.initial_asset_price)
        s += label_to_string("股息率", self.dividend_yield)
        s += label_to_string("融资利差", self.funding_spread)
        s += label_to_string("总回报腿类型", self.total_return_leg.leg_type)
        return s


class CrossBorderTRS:

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
        asset_leg_type: SwapTypes,
        quantity: float,
        initial_asset_price: float,
        is_fixed_qty: bool = True,
        spread: float = 0.0,
        spread_dc_type: DayCountTypes = DayCountTypes.ACT_365F,
        spread_notional_reset: bool = True,
        asset_prices: pd.Series = pd.Series(dtype=np.float64),
        fx_fixing: pd.Series = pd.Series(dtype=np.float64),
        funding_legs: Dict[str, FundingLeg] = {}
    ):
        
        # check_argument_types(self.__init__, locals())

        self.asset_ccy = asset_ccy
        self.settle_ccy = settle_ccy
        self.ccy_pair = ccy_pair
        self.start_dt = start_dt
        self.expiry_dt = expiry_dt
        self.reset_dts = reset_dts
        self.payment_dts = payment_dts
        self.fx_fixing_dts = fx_fixing_dts
        self.asset_leg_type = asset_leg_type
        self.quantity = quantity
        self.initial_asset_price = initial_asset_price
        self.is_fixed_qty = is_fixed_qty 
        self.spread = spread
        self.spread_dc_type = spread_dc_type
        self.spread_notional_reset = spread_notional_reset
        self.asset_prices = asset_prices
        self.fx_fixing = fx_fixing
        self.funding_legs = funding_legs

        if start_dt > expiry_dt:
            raise FinError("Start date after expiry date")

        self.asset_leg = CrossBorderAssetLeg(
            asset_ccy,
            settle_ccy,
            ccy_pair,
            start_dt,
            expiry_dt,
            reset_dts,
            payment_dts,
            fx_fixing_dts,
            asset_leg_type,
            quantity,
            initial_asset_price,
            is_fixed_qty,
            spread,
            spread_dc_type,
            spread_notional_reset,
            asset_prices,
            fx_fixing
        )

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        latest_asset_price: float,
        fx_spot: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        **kwargs
    ):

        asset_leg_pv = self._asset_leg_value(
            value_dt, latest_asset_price, fx_spot, is_only_realized, is_only_unsettled, pv_only=True)
        
        # funding leg is optional
        fixings_dict = kwargs.get("fixings_dict", {})
        funding_leg_pvs = self._funding_legs_value(value_dt, fx_spot, fixings_dict, is_only_realized, is_only_unsettled, pv_only=True)
        funding_leg_pv = sum(funding_leg_pvs.values())

        total_value = asset_leg_pv + funding_leg_pv
        return total_value

    ###########################################################################

    def _asset_leg_value(
        self, 
        value_dt: Date,
        latest_asset_price: float,
        fx_spot: float,
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True
    ):
        asset_leg_pv = self.asset_leg.value(
            value_dt, latest_asset_price, fx_spot,
            is_only_realized, is_only_unsettled, pv_only
        )
        return asset_leg_pv

    ###########################################################################

    def _funding_legs_value(
        self,
        value_dt: Date,
        fx_spot: float,
        fixings_dict: Dict[str, pd.Series] = {},
        is_only_realized: bool = False,
        is_only_unsettled: bool = False,
        pv_only: bool = True,
    ):
        self.funding_leg_pvs = {}

        if self.funding_legs:
            for key, funding_leg in self.funding_legs.items():
                if type(funding_leg) is FixedFundingLeg:
                    leg_pv = funding_leg.value(value_dt, is_only_realized, is_only_unsettled, pv_only)
                elif type(funding_leg) is FloatFundingLeg:
                    fixings = fixings_dict.get(key, {})
                    if not fixings:
                        raise FinError(f"fixing data not provided for {key}")
                    leg_pv = funding_leg.value(value_dt, fixings, is_only_realized, is_only_unsettled, pv_only)
                elif type(funding_leg) is CrossBorderFixedFundingLeg:
                    leg_pv = funding_leg.value(value_dt, fx_spot, is_only_realized, is_only_unsettled, pv_only)
                # elif type(funding_leg) is CrossBorderFloatFundingLeg:
                #     fixings = fixings_dict.get(key, {})
                #     if not fixings:
                #         raise FinError(f"fixing data not provided for {key}")
                #     leg_pv = funding_leg.value(value_dt, fixings, fx_spot, is_only_realized, is_only_unsettled, pv_only)
                else:
                    raise FinError(f'Unsupported funding leg type: {type(funding_leg)}!')
                
                self.funding_leg_pvs[key] = leg_pv
        else:
            logger.info("There's no funding leg for this TRS")
        
        return self.funding_leg_pvs
