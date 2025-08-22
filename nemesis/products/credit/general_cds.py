from copy import deepcopy
from math import exp, log

import numpy as np
from typing import Union
from numba import njit, float64, int64

from ...utils.date import Date
from ...utils.error import FinError
from ...utils.calendar import Calendar, CalendarTypes
from ...utils.calendar import BusDayAdjustTypes, DateGenRuleTypes
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.frequency import annual_frequency, FrequencyTypes
from ...utils.global_vars import g_days_in_year
from ...utils.math import ONE_MILLION
from ...utils.helpers import label_to_string, table_to_string
from ...market.curves.interpolator import InterpTypes, _uinterpolate

from ...utils.helpers import check_argument_types

from .ql_cds_curve import QLCreditCurve

STANDARD_RECOVERY_RATE = 0.40


class GeneralCDS:
    """A class which manages a Credit Default Swap. It performs schedule
    generation and the valuation and risk management of CDS."""

    def __init__(
        self,
        step_in_dt: Date,  # Date protection starts
        maturity_dt_or_tenor: Union[Date, str],  # Date or tenor
        running_cpn: float,  # Annualised cpn on premium fee leg
        notional: float = ONE_MILLION,
        long_protect: bool = True,
        freq_type: FrequencyTypes = FrequencyTypes.QUARTERLY,
        dc_type: DayCountTypes = DayCountTypes.ACT_360,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.FOLLOWING,
        dg_type: DateGenRuleTypes = DateGenRuleTypes.BACKWARD,
    ):
        """Create a CDS from the step-in date, maturity date and cpn"""

        check_argument_types(self.__init__, locals())

        if isinstance(maturity_dt_or_tenor, Date):
            maturity_dt = maturity_dt_or_tenor
        else:
            # To get the next CDS date we move on by the tenor and then roll to
            # the next CDS date after that. We do not holiday adjust it. That
            # is handled in the schedule generation.
            maturity_dt = step_in_dt.add_tenor(maturity_dt_or_tenor)
            maturity_dt = maturity_dt.next_cds_date()

        if step_in_dt > maturity_dt:
            raise FinError("Step in date after maturity date")

        self.step_in_dt = step_in_dt
        self.maturity_dt = maturity_dt
        self.running_cpn = running_cpn
        self.notional = notional
        self.long_protect = long_protect
        self.dc_type = dc_type
        self.dg_type = dg_type
        self.cal_type = cal_type
        self.freq_type = freq_type
        self.bd_type = bd_type

        self._generate_adjusted_cds_payment_dts()
        self._calc_flows()

    ###########################################################################

    def _generate_adjusted_cds_payment_dts(self):
        """Generate CDS payment dates which have been holiday adjusted."""

        frequency = annual_frequency(self.freq_type)
        calendar = Calendar(self.cal_type)
        start_dt = self.step_in_dt

        self.payment_dts = []
        self.accrual_start_dts = []
        self.accrual_end_dts = []
        num_months = int(12.0 / frequency)

        # We generate unadjusted dates - not adjusted for weekends or holidays
        unadjusted_schedule_dts = []

        if self.dg_type == DateGenRuleTypes.BACKWARD:

            # We start at end date and step backwards

            next_dt = self.maturity_dt

            unadjusted_schedule_dts.append(next_dt)

            # the unadjusted dates start at end date and end at previous
            # cpn date
            while next_dt > start_dt:
                next_dt = next_dt.add_months(-num_months)
                unadjusted_schedule_dts.append(next_dt)

            # now we adjust for holiday using business day adjustment
            # convention specified
            adjusted_dts = []

            for date in reversed(unadjusted_schedule_dts):
                adjusted = calendar.adjust(date, self.bd_type)
                adjusted_dts.append(adjusted)

        # eg: https://www.cdsmodel.com/assets/cds-model/docs/Standard%20CDS%20Examples.pdf
        # Payment       = [20-MAR-2009, 22-JUN-2009, 21-SEP-2009, 21-DEC-2009, 22-MAR-2010]
        # Accrual Start = [22-DEC-2008, 20-MAR-2009, 22-JUN-2009, 21-SEP-2009, 21-DEC-2009]
        # Accrual End   = [19-MAR-2009, 21-JUN-2009, 20-SEP-2009, 20-DEC-2009, 20-MAR-2010]

        elif self.dg_type == DateGenRuleTypes.FORWARD:

            # We start at start date and step forwards

            next_dt = start_dt

            # the unadjusted dates start at start date and end at last date
            # before maturity date
            while next_dt < self.maturity_dt:
                unadjusted_schedule_dts.append(next_dt)
                next_dt = next_dt.add_months(num_months)

            # We then append the maturity date
            unadjusted_schedule_dts.append(self.maturity_dt)

            adjusted_dts = []
            for date in unadjusted_schedule_dts:
                adjusted = calendar.adjust(date, self.bd_type)
                adjusted_dts.append(adjusted)

        # eg. Date(20, 2, 2009) to Date(20, 3, 2010) with DateGenRuleTypes.FORWARD
        # Payment       = [20-MAY-2009, 20-AUG-2009, 20-NOV-2009, 22-FEB-2010]
        # Accrual Start = [20-FEB-2009, 20-MAY-2009, 20-AUG-2009, 20-NOV-2009]
        # Accrual End   = [19-MAY-2009, 19-AUG-2009, 19-NOV-2009, 20-MAR-2010]

        else:

            raise FinError("Unknown DateGenRuleType:" + str(self.dg_type))

        # We only include dates which fall after the CDS start date
        self.payment_dts = adjusted_dts[1:]

        # Accrual start dates run from previous cpn date to penultimate
        # cpn date
        self.accrual_start_dts = adjusted_dts[:-1]

        # Accrual end dates are one day before the start of the next
        # accrual period
        self.accrual_end_dts = [
            date.add_days(-1) for date in self.accrual_start_dts[1:]
        ]

        # Final accrual end date is the maturity date
        self.accrual_end_dts.append(self.maturity_dt)

    ###########################################################################

    def _calc_flows(self):
        """Calculate cash flow amounts on premium leg."""
        day_count = DayCount(self.dc_type)

        self.accrual_factors = []
        self.flows = []

        for t0, t1 in zip(self.accrual_start_dts, self.accrual_end_dts):
            # Adding a day because `year_frac` is non-inclusive
            # eg. 20th to 22nd should be 3 days
            accrual_factor = day_count.year_frac(t0, t1.add_days(1))[0]
            flow = accrual_factor * self.running_cpn * self.notional

            self.accrual_factors.append(accrual_factor)
            self.flows.append(flow)

    ###########################################################################

    def value(
        self,
        value_dt,
        issuer_curve,
        contract_recovery_rate=STANDARD_RECOVERY_RATE
    ):
        """Valuation of a CDS contract on a specific valuation date given
        an issuer curve and a contract recovery rate."""

        rpv01 = self.risky_pv01(value_dt, issuer_curve)

        dirty_rpv01 = rpv01["dirty_rpv01"]
        clean_rpv01 = rpv01["clean_rpv01"]

        prot_pv = self.prot_leg_pv(
            value_dt,
            issuer_curve,
            contract_recovery_rate
        )

        fwd_df = 1.0

        if self.long_protect:
            long_prot = +1
        else:
            long_prot = -1

        dirty_pv = (
            fwd_df
            * long_prot
            * (prot_pv - self.running_cpn * dirty_rpv01 * self.notional)
        )
        clean_pv = (
            fwd_df
            * long_prot
            * (prot_pv - self.running_cpn * clean_rpv01 * self.notional)
        )

        return {"dirty_pv": dirty_pv, "clean_pv": clean_pv}

    ###########################################################################

    def credit_dv01(
        self,
        value_dt,
        issuer_curve,
        contract_recovery_rate,
        bump=0.0001  # 1 basis point
    ):
        """Calculation of the change in the value of the CDS contract for a
        one basis point change in the level of the CDS curve."""

        if issuer_curve._from_ql:

            ql_credit_curve_up = issuer_curve.ql_cds_curve.tweak_parallel(bump)
            credit_curve_up = QLCreditCurve(value_dt, ql_credit_curve_up)
            ql_credit_curve_down = issuer_curve.ql_cds_curve.tweak_parallel(-bump)
            credit_curve_down = QLCreditCurve(value_dt, ql_credit_curve_down)

        else:

            v0 = self.value(
                value_dt,
                issuer_curve,
                contract_recovery_rate
            )

            # we create a deep copy to avoid state issues
            bumpedIssuerCurve = deepcopy(issuer_curve)
            for cds in bumpedIssuerCurve.cds_contracts:
                cds.running_cpn += bump

            bumpedIssuerCurve._build_curve()

            v1 = self.value(
                value_dt,
                bumpedIssuerCurve,
                contract_recovery_rate
            )

            credit_dv01 = v1["dirty_pv"] - v0["dirty_pv"]

        npv_up = self.value(value_dt, credit_curve_up)
        npv_down = self.value(value_dt, credit_curve_down)

        credit_dv01 = (npv_up["dirty_pv"] - npv_down["dirty_pv"]) / (2 * bump)

        return credit_dv01

    ###########################################################################

    def interest_dv01(
        self,
        value_dt: Date,
        issuer_curve,
        contract_recovery_rate,
        bump=0.0001  # 1 basis point
    ):
        """Calculation of the interest DV01 based on a simple bump of
        the discount factors and reconstruction of the CDS curve."""

        if issuer_curve._from_ql:
        
            ql_credit_curve_up = issuer_curve.ql_cds_curve.tweak_parallel(bump)
            credit_curve_up = QLCreditCurve(value_dt, ql_credit_curve_up)
            ql_credit_curve_down = issuer_curve.ql_cds_curve.tweak_parallel(-bump)
            credit_curve_down = QLCreditCurve(value_dt, ql_credit_curve_down)

            # ql_discount_curve_up = issuer_curve.libor_curve.ql_curve.tweak_parallel(bump)
            ql_credit_curve_up = issuer_curve.ql_cds_curve.tweak_discount(bump)
            credit_curve_up = QLCreditCurve(value_dt, ql_credit_curve_up)
            ql_credit_curve_down = issuer_curve.ql_cds_curve.tweak_discount(-bump)
            credit_curve_down = QLCreditCurve(value_dt, ql_credit_curve_down)

        else:
        
            v0 = self.value(
                value_dt,
                issuer_curve,
                contract_recovery_rate
            )

            # we create a deep copy to avoid state issues
            new_issuer_curve = deepcopy(issuer_curve)

            for depo in new_issuer_curve.libor_curve.used_deposits:

                depo.deposit_rate += bump

            for fra in new_issuer_curve.libor_curve.used_fras:

                fra.fra_rate += bump

            for swap in new_issuer_curve.libor_curve.used_swaps:

                cpn = swap.fixed_leg.cpn
                swap.fixed_leg.cpn = cpn + bump

                # Need to regenerate fixed leg payments with bumped cpn
                # I could call swap.fixed_leg.generate_payments() but it is
                # overkill as it has to do all the schedule generation which is
                # not needed as the dates are unchanged
                num_payments = len(swap.fixed_leg.payments)
                for i in range(0, num_payments):
                    old_pmt = swap.fixed_leg.payments[i]
                    swap.fixed_leg.payments[i] = old_pmt * (cpn + bump) / cpn

            new_issuer_curve.libor_curve._build_curve()
            new_issuer_curve._build_curve()

            v1 = self.value(
                value_dt,
                new_issuer_curve,
                contract_recovery_rate
            )

            interest_dv01 = v1["dirty_pv"] - v0["dirty_pv"]
        
        npv_up = self.value(value_dt, credit_curve_up)
        npv_down = self.value(value_dt, credit_curve_down)

        interest_dv01 = (npv_up["dirty_pv"] - npv_down["dirty_pv"]) / (2 * bump) * 1e-4

        return interest_dv01

    ###########################################################################

    def cash_settlement_amount(
        self,
        value_dt,
        settle_dt,
        issuer_curve,
        contract_recovery_rate
    ):
        """Value of the contract on the settlement date including accrued
        interest."""

        v = self.value(
            value_dt,
            issuer_curve,
            contract_recovery_rate
        )

        libor_curve = issuer_curve.libor_curve
        df = libor_curve.df(settle_dt, day_count=DayCountTypes.ACT_365F)
        v = v / df
        return v

    ###########################################################################

    def clean_price(
        self,
        value_dt,
        issuer_curve,
        contract_recovery_rate
    ):
        """Value of the CDS contract excluding accrued interest."""

        risky_pv01 = self.risky_pv01(value_dt, issuer_curve)

        clean_rpv01 = risky_pv01["clean_rpv01"]

        prot_pv = self.prot_leg_pv(
            value_dt,
            issuer_curve,
            contract_recovery_rate
        )

        fwd_df = 1.0

        clean_pv = fwd_df * (
            prot_pv - self.running_cpn * clean_rpv01 * self.notional
        )

        clean_price = (self.notional - clean_pv) / self.notional * 100.0

        return clean_price

    ###########################################################################

    def accrued_days(self):
        """Number of days between the previous coupon and the currrent step
        in date."""

        # I assume accrued runs to the effective date
        pcd = self.accrual_start_dts[0]
        accrued_days = self.step_in_dt.add_days(1) - pcd
        return accrued_days

    ###########################################################################

    def accrued_interest(self):
        """Calculate the amount of accrued interest that has accrued from the
        previous cpn date (PCD) to the step_in_dt of the CDS contract."""

        day_count = DayCount(self.dc_type)
        pcd = self.accrual_start_dts[0]
        accrual_factor = day_count.year_frac(pcd, self.step_in_dt.add_days(1))[0]
        accrued_interest = accrual_factor * self.notional * self.running_cpn

        if self.long_protect:
            accrued_interest *= -1.0

        return accrued_interest

    ###########################################################################
    
    def prot_leg_pv(
        self,
        value_dt,
        issuer_curve,
        contract_recovery_rate=STANDARD_RECOVERY_RATE
    ):
        """Calculates the protection leg PV using devlib's exact day-by-day method.
        
        This is a separate method to avoid breaking curve construction while
        providing exact devlib compatibility for final valuations.
        """
        
        # Calculate the number of days for the protection period
        step_in_days = int(self.step_in_dt - value_dt)
        maturity_days = int(self.maturity_dt - value_dt)
        
        prot_pv = 0.0
        
        # Day-by-day calculation exactly like devlib
        for day in range(step_in_days, maturity_days):
            # Convert day to Date objects for curve lookups
            date_start = value_dt.add_days(day)
            date_end = value_dt.add_days(day + 1)
            
            # Ensure we don't exceed maturity
            if date_end > self.maturity_dt:
                date_end = self.maturity_dt
            
            # Get survival probabilities at day boundaries
            s_start = issuer_curve.survival_prob(date_start)
            s_end = issuer_curve.survival_prob(date_end)
            
            # Get discount factor for payment at day end
            libor_curve = issuer_curve.libor_curve
            df_end = libor_curve.df(date_end, day_count=DayCountTypes.ACT_365F)
            
            # Calculate daily default probability
            default_prob = s_start - s_end
            
            # Daily protection leg contribution
            # if default_prob > 0 and df_end > 0:
            daily_contribution = default_prob * df_end * (1.0 - contract_recovery_rate)
            prot_pv += daily_contribution
        
        return prot_pv * self.notional

    ###########################################################################

    def risky_pv01(self, value_dt, issuer_curve, coupon_accrued=True):
        """The risky_pv01 is the present value of a risky one dollar paid on
        the premium leg of a CDS contract."""

        libor_curve = issuer_curve.libor_curve

        # this is the part of the cpn accrued from the previous cpn date
        # to now
        pcd = self.accrual_start_dts[0]
        ncd = self.accrual_end_dts[0]
        eff = self.step_in_dt
        cpd = self.payment_dts[0]

        day_count = DayCount(self.dc_type)

        accrual_factor_pcd_to_now = day_count.year_frac(pcd, eff.add_days(1))[0]

        year_fracs = self.accrual_factors

        # The first cpn is a special case which needs to be handled carefully
        # taking into account what cpn has already accrued and what has not
        q1 = issuer_curve.survival_prob(ncd)
        z1 = libor_curve.df(cpd, day_count=DayCountTypes.ACT_365F)

        # reference credit survives to the premium payment date
        full_rpv01 = q1 * z1 * year_fracs[0]

        first_period_accrual_pv = 0.0
        step_in_days = int(self.step_in_dt - value_dt)
        first_period_end_days = int(ncd - value_dt)

        for day in range(step_in_days, first_period_end_days):

            date_start = value_dt.add_days(day)
            date_end = value_dt.add_days(day + 1)
            
            # Ensure we don't exceed maturity
            if date_end > self.maturity_dt:
                date_end = self.maturity_dt
            
            # Get survival probabilities at day boundaries
            s_start = issuer_curve.survival_prob(date_start)
            s_end = issuer_curve.survival_prob(date_end)
            
            # Get discount factor for payment at day end
            libor_curve = issuer_curve.libor_curve
            df_end = libor_curve.df(date_end, day_count=DayCountTypes.ACT_365F)
            
            # Calculate daily default probability
            default_prob = s_start - s_end
            daily_contribution = default_prob * df_end * day_count.year_frac(pcd, date_end)[0]
            first_period_accrual_pv += daily_contribution
        
        full_rpv01 += first_period_accrual_pv

        for it in range(1, len(self.payment_dts)):

            pcd = self.accrual_start_dts[it]
            ncd = self.accrual_end_dts[it]
            cpd = self.payment_dts[it]

            q2 = issuer_curve.survival_prob(ncd)
            z2 = libor_curve.df(cpd, day_count=DayCountTypes.ACT_365F)

            accrual_factor = year_fracs[it]

            # full cpn is paid at the end of the current period if survives to
            # payment date
            full_rpv01 += q2 * z2 * accrual_factor

            #######################################################################

            if coupon_accrued:

                period_accrual_pv = 0.0
                period_end_days = int(ncd - pcd)
                
                for day in range(0, period_end_days):
                    # Convert day to Date objects for curve lookups
                    date_start = pcd.add_days(day)
                    date_end = pcd.add_days(day + 1)
                    
                    # Ensure we don't exceed maturity
                    if date_end > self.maturity_dt:
                        date_end = self.maturity_dt
                    
                    # Get survival probabilities at day boundaries
                    s_start = issuer_curve.survival_prob(date_start)
                    s_end = issuer_curve.survival_prob(date_end)
                    
                    # Get discount factor for payment at day end
                    libor_curve = issuer_curve.libor_curve
                    df_end = libor_curve.df(date_end, day_count=DayCountTypes.ACT_365F)
                    
                    # Calculate daily default probability
                    default_prob = s_start - s_end
                    daily_contribution = default_prob * df_end * day_count.year_frac(pcd, date_end)[0]
                    period_accrual_pv += daily_contribution
                    
                    d_full_rpv01 = period_accrual_pv
            
            full_rpv01 = full_rpv01 + d_full_rpv01
            q1 = q2

        clean_rpv01 = full_rpv01 - accrual_factor_pcd_to_now

        return {"dirty_rpv01": full_rpv01, "clean_rpv01": clean_rpv01}

    ###########################################################################

    def premium_leg_pv(self, value_dt, issuer_curve):
        """Value of the premium leg of a CDS."""

        full_rpv01 = self.risky_pv01(value_dt, issuer_curve)[
            "dirty_rpv01"
        ]

        v = full_rpv01 * self.notional * self.running_cpn
        return v

    ###########################################################################

    def par_spread(
        self,
        value_dt,
        issuer_curve,
        contract_recovery_rate=STANDARD_RECOVERY_RATE
    ):
        """Breakeven CDS cpn that would make the value of the CDS contract
        equal to zero."""

        clean_rpv01 = self.risky_pv01(value_dt, issuer_curve)[
            "clean_rpv01"
        ]

        prot = self.prot_leg_pv(
            value_dt,
            issuer_curve,
            contract_recovery_rate
        )

        # By convention this is calculated using the clean RPV01
        spd = prot / clean_rpv01 / self.notional
        return spd
  
    ###########################################################################

    def print_payments(self, value_dt, issuer_curve):
        """We only print payments after the current valuation date"""
        num_flows = len(self.payment_dts)

        print(
            "PAYMENT_dt      YEAR_FRAC      FLOW           DF       SURV_PROB      NPV"
        )

        for it in range(0, num_flows):
            dt = self.payment_dts[it]

            if dt > value_dt:
                acc_factor = self.accrual_factors[it]
                flow = self.flows[it]
                z = issuer_curve.libor_curve.df(dt, day_count=DayCountTypes.ACT_365F)
                q = issuer_curve.survival_prob(dt)
                print(
                    "%15s %10.6f %12.2f %12.6f %12.6f %12.2f"
                    % (dt, acc_factor, flow, z, q, flow * z * q)
                )

    ###########################################################################

    def __repr__(self):
        """print out details of the CDS contract and all the calculated
        cash flows"""
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("STEP-IN DATE", self.step_in_dt)
        s += label_to_string("MATURITY", self.maturity_dt)
        s += label_to_string("NOTIONAL", self.notional)
        s += label_to_string("RUN COUPON", self.running_cpn * 10000, "bp\n")
        s += label_to_string("DAYCOUNT", self.dc_type)
        s += label_to_string("FREQUENCY", self.freq_type)
        s += label_to_string("CALENDAR", self.cal_type)
        s += label_to_string("BUSDAYRULE", self.bd_type)
        s += label_to_string("DATEGENRULE", self.dg_type)
        s += label_to_string("ACCRUED DAYS", self.accrued_days())

        header = "PAYMENT_dt, YEAR_FRAC, ACCRUAL_START, ACCRUAL_END, FLOW"
        value_table = [
            self.payment_dts,
            self.accrual_factors,
            self.accrual_start_dts,
            self.accrual_end_dts,
            self.flows,
        ]
        precision = "12.6f"

        s += table_to_string(header, value_table, precision)

        return s

    ###########################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)


###############################################################################
