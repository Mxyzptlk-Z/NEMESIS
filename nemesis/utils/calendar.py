import datetime
from chinese_calendar import is_holiday
from enum import Enum
from .date import Date
from .error import FinError

# from numba import njit, jit, int64, boolean

easterMondayDay = [98, 90, 103, 95, 114, 106, 91, 111, 102, 87,
                   107, 99, 83, 103, 95, 115, 99, 91, 111, 96, 87,
                   107, 92, 112, 103, 95, 108, 100, 91,
                   111, 96, 88, 107, 92, 112, 104, 88, 108, 100,
                   85, 104, 96, 116, 101, 92, 112, 97, 89, 108,
                   100, 85, 105, 96, 109, 101, 93, 112, 97, 89,
                   109, 93, 113, 105, 90, 109, 101, 86, 106, 97,
                   89, 102, 94, 113, 105, 90, 110, 101, 86, 106,
                   98, 110, 102, 94, 114, 98, 90, 110, 95, 86,
                   106, 91, 111, 102, 94, 107, 99, 90, 103, 95,
                   115, 106, 91, 111, 103, 87, 107, 99, 84, 103,
                   95, 115, 100, 91, 111, 96, 88, 107, 92, 112,
                   104, 95, 108, 100, 92, 111, 96, 88, 108, 92,
                   112, 104, 89, 108, 100, 85, 105, 96, 116, 101,
                   93, 112, 97, 89, 109, 100, 85, 105, 97, 109,
                   101, 93, 113, 97, 89, 109, 94, 113, 105, 90,
                   110, 101, 86, 106, 98, 89, 102, 94, 114, 105,
                   90, 110, 102, 86, 106, 98, 111, 102, 94, 114,
                   99, 90, 110, 95, 87, 106, 91, 111, 103, 94,
                   107, 99, 91, 103, 95, 115, 107, 91, 111, 103,
                   88, 108, 100, 85, 105, 96, 109, 101, 93, 112,
                   97, 89, 109, 93, 113, 105, 90, 109, 101, 86,
                   106, 97, 89, 102, 94, 113, 105, 90, 110, 101,
                   86, 106, 98, 110, 102, 94, 114, 98, 90, 110,
                   95, 86, 106, 91, 111, 102, 94, 107, 99, 90,
                   103, 95, 115, 106, 91, 111, 103, 87, 107, 99,
                   84, 103, 95, 115, 100, 91, 111, 96, 88, 107,
                   92, 112, 104, 95, 108, 100, 92, 111, 96, 88,
                   108, 92, 112, 104, 89, 108, 100, 85, 105, 96,
                   116, 101, 93, 112, 97, 89, 109, 100, 85, 105]


class BusDayAdjustTypes(Enum):
    NONE = 1
    FOLLOWING = 2
    MODIFIED_FOLLOWING = 3
    PRECEDING = 4
    MODIFIED_PRECEDING = 5


class CalendarTypes(Enum):
    NONE = 1
    WEEKEND = 2
    AUSTRALIA = 3
    CANADA = 4
    FRANCE = 5
    GERMANY = 6
    ITALY = 7
    JAPAN = 8
    NEW_ZEALAND = 9
    NORWAY = 10
    SWEDEN = 11
    SWITZERLAND = 12
    TARGET = 13
    UNITED_STATES = 14
    UNITED_KINGDOM = 15
    CHINA = 16
    JOINT = 17


class DateGenRuleTypes(Enum):
    FORWARD = 1
    BACKWARD = 2

###############################################################################


class Calendar:
    """ Class to manage designation of payment dates as holidays according to
    a regional or country-specific calendar convention specified by the user.
    It also supplies an adjustment method which takes in an adjustment
    convention and then applies that to any date that falls on a holiday in the
    specified calendar. """

    def __init__(self, cal_type):
        """ Create a calendar based on a specified calendar type. """

        # 修改这里，允许传入 JointCalendar 实例
        if isinstance(cal_type, CalendarTypes):
            self.cal_type = cal_type
            self.joint_calendar = None
        elif isinstance(cal_type, JointCalendar):
            self.cal_type = CalendarTypes.JOINT
            self.joint_calendar = cal_type
        else:
            raise FinError(
                "Need to pass FinCalendarType or JointCalendar and not " +
                str(cal_type))

        self.day_in_year = None
        self.weekday = None

    ###########################################################################

    def adjust(self,
               dt: Date,
               bd_type: BusDayAdjustTypes):
        """ Adjust a payment date if it falls on a holiday according to the
        specified business day convention. """

        if isinstance(bd_type, BusDayAdjustTypes) is False:
            raise FinError("Invalid type passed. Need Finbd_type")

        # If calendar type is NONE then every day is a business day
        if self.cal_type == CalendarTypes.NONE:
            return dt

        if bd_type == BusDayAdjustTypes.NONE:
            return dt

        elif bd_type == BusDayAdjustTypes.FOLLOWING:

            # step forward until we find a business day
            while self.is_business_day(dt) is False:
                dt = dt.add_days(1)

            return dt

        elif bd_type == BusDayAdjustTypes.MODIFIED_FOLLOWING:

            d_start = dt.d
            m_start = dt.m
            y_start = dt.y

            # step forward until we find a business day
            while self.is_business_day(dt) is False:
                dt = dt.add_days(1)

            # if the business day is in a different month look back
            # for previous first business day one day at a time
            # TODO: I could speed this up by starting it at initial date
            if dt.m != m_start:
                dt = Date(d_start, m_start, y_start)
                while self.is_business_day(dt) is False:
                    dt = dt.add_days(-1)

            return dt

        elif bd_type == BusDayAdjustTypes.PRECEDING:

            # if the business day is in the next month look back
            # for previous first business day one day at a time
            while self.is_business_day(dt) is False:
                dt = dt.add_days(-1)

            return dt

        elif bd_type == BusDayAdjustTypes.MODIFIED_PRECEDING:

            d_start = dt.d
            m_start = dt.m
            y_start = dt.y

            # step backward until we find a business day
            while self.is_business_day(dt) is False:
                dt = dt.add_days(-1)

            # if the business day is in a different month look forward
            # for previous first business day one day at a time
            # I could speed this up by starting it at initial date
            if dt.m != m_start:
                dt = Date(d_start, m_start, y_start)
                while self.is_business_day(dt) is False:
                    dt = dt.add_days(+1)

            return dt

        else:

            raise FinError("Unknown adjustment convention" +
                           str(bd_type))

        return dt

###############################################################################

    def add_business_days(self,
                          start_dt: Date,
                          num_days: int):
        """ Returns a new date that is num_days business days after Date.
        All holidays in the chosen calendar are assumed not business days. """

        # TODO: REMOVE DATETIME DEPENDENCE HERE ???

        if isinstance(num_days, int) is False:
            raise FinError("Num days must be an integer")

        dt = datetime.date(start_dt.y, start_dt.m, start_dt.d)
        d = dt.day
        m = dt.month
        y = dt.year
        new_dt = Date(d, m, y)

        s = +1
        if num_days < 0:
            num_days = -1 * num_days
            s = -1

        while num_days > 0:
            dt = dt + s * datetime.timedelta(days=1)
            d = dt.day
            m = dt.month
            y = dt.year
            new_dt = Date(d, m, y)

            if self.is_business_day(new_dt) is True:
                num_days -= 1

        return new_dt

###############################################################################

    def is_business_day(self,
                        dt: Date):
        """ Determines if a date is a business day according to the specified
        calendar. If it is it returns True, otherwise False. """

        # 如果是联合日历，使用联合日历的逻辑
        if self.cal_type == CalendarTypes.JOINT and self.joint_calendar is not None:
            return self.joint_calendar.is_business_day(dt)

        # For all calendars so far, SAT and SUN are not business days
        # If this ever changes I will need to add a filter here.
        if dt.is_weekend():
            return False

        if self.is_holiday(dt) is True:
            return False
        else:
            return True

###############################################################################

    def is_holiday(self,
                   dt: Date):
        """ Determines if a date is a Holiday according to the specified
        calendar. Weekends are not holidays unless the holiday falls on a
        weekend date. """

        # 如果是联合日历，使用联合日历的逻辑
        if self.cal_type == CalendarTypes.JOINT and self.joint_calendar is not None:
            return self.joint_calendar.is_holiday(dt)

        start_dt = Date(1, 1, dt.y)
        self.day_in_year = dt.excel_dt - start_dt.excel_dt + 1
        self.weekday = dt.weekday

        if self.cal_type == CalendarTypes.NONE:
            return self.holiday_none(dt)
        elif self.cal_type == CalendarTypes.WEEKEND:
            return self.holiday_weekend(dt)
        elif self.cal_type == CalendarTypes.AUSTRALIA:
            return self.holiday_australia(dt)
        elif self.cal_type == CalendarTypes.CANADA:
            return self.holiday_canada(dt)
        elif self.cal_type == CalendarTypes.FRANCE:
            return self.holiday_france(dt)
        elif self.cal_type == CalendarTypes.GERMANY:
            return self.holiday_germany(dt)
        elif self.cal_type == CalendarTypes.ITALY:
            return self.holiday_italy(dt)
        elif self.cal_type == CalendarTypes.JAPAN:
            return self.holiday_japan(dt)
        elif self.cal_type == CalendarTypes.NEW_ZEALAND:
            return self.holiday_new_zealand(dt)
        elif self.cal_type == CalendarTypes.NORWAY:
            return self.holiday_norway(dt)
        elif self.cal_type == CalendarTypes.SWEDEN:
            return self.holiday_sweden(dt)
        elif self.cal_type == CalendarTypes.SWITZERLAND:
            return self.holiday_switzerland(dt)
        elif self.cal_type == CalendarTypes.TARGET:
            return self.holiday_target(dt)
        elif self.cal_type == CalendarTypes.UNITED_KINGDOM:
            return self.holiday_united_kingdom(dt)
        elif self.cal_type == CalendarTypes.UNITED_STATES:
            return self.holiday_united_states(dt)
        elif self.cal_type == CalendarTypes.CHINA:
            return self.holiday_china(dt)
        elif self.cal_type == CalendarTypes.JOINT:
            # 对于联合日历类型，使用 JointCalendar 的逻辑
            # 但这里不会被调用，因为 JointCalendar 重写了 is_holiday 方法
            return False
        else:
            print(self.cal_type)
            raise FinError("Unknown calendar")

###############################################################################

    def holiday_weekend(self, dt: Date):
        """ Weekends by themselves are a holiday. """

        if dt.is_weekend():
            return True
        else:
            return False

###############################################################################

    def holiday_australia(self, dt: Date):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 26:  # Australia day
            return True

        if m == 1 and d == 27 and weekday == Date.MON:  # Australia day
            return True

        if m == 1 and d == 28 and weekday == Date.MON:  # Australia day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 3:  # good friday
            return True

        if day_in_year == em:  # Easter Monday
            return True

        if m == 4 and d == 25:  # Australia day
            return True

        if m == 4 and d == 26 and weekday == Date.MON:  # Australia day
            return True

        if m == 6 and d > 7 and d < 15 and weekday == Date.MON:  # Queen
            return True

        if m == 8 and d < 8 and weekday == Date.MON:  # BANK holiday
            return True

        if m == 10 and d < 8 and weekday == Date.MON:  # BANK holiday
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Boxing
            return True

        if m == 12 and d == 28 and weekday == Date.MON:  # Boxing
            return True

        return False

###############################################################################

    def holiday_united_kingdom(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 2 and weekday == Date.MON:  # new years day
            return True

        if m == 1 and d == 3 and weekday == Date.MON:  # new years day
            return True

        em = easterMondayDay[y - 1901]

        if self.day_in_year == em:  # Easter Monday
            return True

        if self.day_in_year == em - 3:  # good friday
            return True

        if m == 5 and d <= 7 and weekday == Date.MON:
            return True

        if m == 5 and d >= 25 and weekday == Date.MON:
            return True

        if m == 6 and d == 2 and y == 2022:  # SPRING BANK HOLIDAY
            return True

        if m == 6 and d == 3 and y == 2022:  # QUEEN PLAT JUB
            return True

        if m == 8 and d > 24 and weekday == Date.MON:  # Late Summer
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 27 and weekday == Date.TUE:  # Xmas
            return True

        if m == 12 and d == 28 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 28 and weekday == Date.TUE:  # Xmas
            return True

        return False

###############################################################################

    def holiday_france(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year

        if m == 1 and d == 1:  # new years day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em - 3:  # good friday
            return True

        if m == 5 and d == 1:  # LABOUR DAY
            return True

        if m == 5 and d == 8:  # VICTORY DAY
            return True

        if day_in_year == em + 39 - 1:  # Ascension
            return True

        if day_in_year == em + 50 - 1:  # pentecost
            return True

        if m == 7 and d == 14:  # BASTILLE DAY
            return True

        if m == 8 and d == 15:  # ASSUMPTION
            return True

        if m == 11 and d == 1:  # ALL SAINTS
            return True

        if m == 11 and d == 11:  # ARMISTICE
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        return False

###############################################################################

    def holiday_sweden(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 6:  # epiphany day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 3:  # good friday
            return True

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em + 39 - 1:  # Ascension
            return True

        if m == 5 and d == 1:  # labour day
            return True

        if m == 6 and d == 6:  # June
            return True

        if m == 6 and d > 18 and d < 26 and weekday == Date.FRI:  # Midsummer
            return True

        if m == 12 and d == 24:  # Xmas eve
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        if m == 12 and d == 31:  # NYE
            return True

        return False

###############################################################################

    def holiday_germany(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year

        if m == 1 and d == 1:  # new years day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em - 3:  # good friday
            return True

        if m == 5 and d == 1:  # LABOUR DAY
            return True

        if day_in_year == em + 39 - 1:  # Ascension
            return True

        if day_in_year == em + 50 - 1:  # pentecost
            return True

        if m == 10 and d == 3:  # GERMAN UNITY DAY
            return True

        if m == 12 and d == 24:  # Xmas eve
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        return False

###############################################################################

    def holiday_switzerland(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 2:  # berchtoldstag
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em - 3:  # good friday
            return True

        if day_in_year == em + 39 - 1:  # Ascension
            return True

        if day_in_year == em + 50 - 1:  # pentecost / whit
            return True

        if m == 5 and d == 1:  # Labour day
            return True

        if m == 8 and d == 1:  # National day
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        return False

###############################################################################

    def holiday_japan(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 2 and weekday == Date.MON:  # bank holiday
            return True

        if m == 1 and d == 3 and weekday == Date.MON:  # bank holiday
            return True

        if m == 1 and d > 7 and d < 15 and weekday == Date.MON:  # coa
            return True

        if m == 2 and d == 11:  # nfd
            return True

        if m == 2 and d == 12 and weekday == Date.MON:  # nfd
            return True

        if m == 2 and d == 23:  # emperor's birthday
            return True

        if m == 2 and d == 24 and weekday == Date.MON:  # emperor's birthday
            return True

        if m == 3 and d == 20:  # vernal equinox - NOT EXACT
            return True

        if m == 3 and d == 21 and weekday == Date.MON:
            return True

        if m == 4 and d == 29:  # SHOWA greenery
            return True

        if m == 4 and d == 30 and weekday == Date.MON:  # SHOWA greenery
            return True

        if m == 5 and d == 3:  # Memorial Day
            return True

        if m == 5 and d == 4:  # nation
            return True

        if m == 5 and d == 5:  # children
            return True

        if m == 5 and d == 6 and weekday == Date.MON:  # children
            return True

        if m == 7 and d > 14 and d < 22 and y != 2021 and weekday == Date.MON:
            return True

        if m == 7 and d == 22 and y == 2021:  # OLYMPICS
            return True

        if m == 7 and d == 23 and y == 2021:  # OLYMPICS HEALTH AND SPORTS HERE
            return True

        # Mountain day
        if m == 8 and d == 11 and y != 2021:
            return True

        if m == 8 and d == 12 and y != 2021 and weekday == Date.MON:
            return True

        if m == 8 and d == 9 and y == 2021 and weekday == Date.MON:
            return True

        # Respect for aged
        if m == 9 and d > 14 and d < 22 and weekday == Date.MON:
            return True

        # Equinox - APPROXIMATE
        if m == 9 and d == 23:
            return True

        if m == 9 and d == 24 and weekday == Date.MON:
            return True

        if m == 10 and d > 7 and d <= 14 and y != 2021 and weekday == Date.MON:  # HS
            return True

        if m == 11 and d == 3:  # Culture
            return True

        if m == 11 and d == 4 and weekday == Date.MON:  # Culture
            return True

        if m == 11 and d == 23:  # Thanksgiving
            return True

        return False

###############################################################################

    def holiday_new_zealand(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 2 and weekday == Date.MON:  # new years day
            return True

        if m == 1 and d == 3 and weekday == Date.MON:  # new years day
            return True

        if m == 1 and d > 18 and d < 26 and weekday == Date.MON:  # Anniversary
            return True

        if m == 2 and d == 6:  # Waitanga day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 3:  # good friday
            return True

        if day_in_year == em:  # Easter Monday
            return True

        if m == 4 and d == 25:  # ANZAC day
            return True

        if m == 6 and d < 8 and weekday == Date.MON:  # Queen
            return True

        if m == 10 and d > 21 and d < 29 and weekday == Date.MON:  # LABOR DAY
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Boxing
            return True

        if m == 12 and d == 28 and weekday == Date.MON:  # Boxing
            return True

        return False

###############################################################################

    def holiday_norway(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # new years day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 4:  # holy thursday
            return True

        if day_in_year == em - 3:  # good friday
            return True

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em + 38:  # Ascension
            return True

        if day_in_year == em + 49:  # Pentecost
            return True

        if m == 5 and d == 1:  # May day
            return True

        if m == 5 and d == 17:  # Independence day
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        return False

###############################################################################

    def holiday_united_states(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday.
        This is a generic US calendar that contains the superset of
        holidays for bond markets, NYSE, and public holidays. For each of
        these and other categories there will be some variations. """

        m = dt.m
        d = dt.d
        weekday = self.weekday

        if m == 1 and d == 1:  # NYD
            return True

        if m == 1 and d == 2 and weekday == Date.MON:  # NYD
            return True

        if m == 1 and d == 3 and weekday == Date.MON:  # NYD
            return True

        if m == 1 and d >= 15 and d < 22 and weekday == Date.MON:  # MLK
            return True

        if m == 2 and d >= 15 and d < 22 and weekday == Date.MON:  # GW
            return True

        if m == 5 and d >= 25 and d <= 31 and weekday == Date.MON:  # MD
            return True
        
        if m == 6 and d == 19:  # Juneteenth day
            return True

        if m == 7 and d == 4:  # Indep day
            return True

        if m == 7 and d == 5 and weekday == Date.MON:  # Indep day
            return True

        if m == 7 and d == 3 and weekday == Date.FRI:  # Indep day
            return True

        if m == 9 and d >= 1 and d < 8 and weekday == Date.MON:  # Lab
            return True

        if m == 10 and d >= 8 and d < 15 and weekday == Date.MON:  # CD
            return True

        if m == 11 and d == 11:  # Veterans day
            return True

        if m == 11 and d == 12 and weekday == Date.MON:  # Vets
            return True

        if m == 11 and d == 10 and weekday == Date.FRI:  # Vets
            return True

        if m == 11 and d >= 22 and d < 29 and weekday == Date.THU:  # TG
            return True

        if m == 12 and d == 24 and weekday == Date.FRI:  # Xmas holiday
            return True

        if m == 12 and d == 25:  # Xmas holiday
            return True

        if m == 12 and d == 26 and weekday == Date.MON:  # Xmas holiday
            return True

        if m == 12 and d == 31 and weekday == Date.FRI:
            return True

        return False

###############################################################################

    def holiday_canada(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year
        weekday = self.weekday

        if m == 1 and d == 1:  # NYD
            return True

        if m == 1 and d == 2 and weekday == Date.MON:  # NYD
            return True

        if m == 1 and d == 3 and weekday == Date.MON:  # NYD
            return True

        if m == 2 and d >= 15 and d < 22 and weekday == Date.MON:  # FAMILY
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 3:  # good friday
            return True

        if m == 5 and d >= 18 and d < 25 and weekday == Date.MON:  # VICTORIA
            return True

        if m == 7 and d == 1:  # Canada day
            return True

        if m == 7 and d == 2 and weekday == Date.MON:  # Canada day
            return True

        if m == 7 and d == 3 and weekday == Date.MON:  # Canada day
            return True

        if m == 8 and d < 8 and weekday == Date.MON:  # Provincial
            return True

        if m == 9 and d < 8 and weekday == Date.MON:  # Labor
            return True

        if m == 10 and d >= 8 and d < 15 and weekday == Date.MON:  # THANKS
            return True

        if m == 11 and d == 11:  # Veterans day
            return True

        if m == 11 and d == 12 and weekday == Date.MON:  # Vets
            return True

        if m == 11 and d == 13 and weekday == Date.MON:  # Vets
            return True

        if m == 12 and d == 25:  # Xmas holiday
            return True

        if m == 12 and d == 26 and weekday == Date.MON:  # Xmas holiday
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Xmas holiday
            return True

        if m == 12 and d == 26:  # Boxing holiday
            return True

        if m == 12 and d == 27 and weekday == Date.MON:  # Boxing holiday
            return True

        if m == 12 and d == 28 and weekday == Date.TUE:  # Boxing holiday
            return True

        return False

###############################################################################

    def holiday_italy(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year

        if m == 1 and d == 1:  # new years day
            return True

        if m == 1 and d == 6:  # epiphany
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em:  # Easter Monday
            return True

        if day_in_year == em - 3:  # good friday
            return True

        if m == 4 and d == 25:  # LIBERATION DAY
            return True

        if m == 5 and d == 1:  # LABOUR DAY
            return True

        if m == 6 and d == 2 and y > 1999:  # REPUBLIC DAY
            return True

        if m == 8 and d == 15:  # ASSUMPTION
            return True

        if m == 11 and d == 1:  # ALL SAINTS
            return True

        if m == 12 and d == 8:  # IMMAC CONC
            return True

        if m == 12 and d == 25:  # Xmas
            return True

        if m == 12 and d == 26:  # Boxing day
            return True

        return False

###############################################################################

    def holiday_china(self, dt: Date):
        """ Chiense legal holidays, exclude weekends."""
        
        m = dt.m
        d = dt.d
        y = dt.y
        weekday = self.weekday

        date = datetime.date(y, m, d)

        if y >= 2026:
            if weekday == Date.SAT or weekday == Date.SUN:
                return True
            else:
                return False
        else:
            if weekday == Date.SAT or weekday == Date.SUN:
                return False
            else:
                return is_holiday(date)

###############################################################################

    def holiday_target(self, dt):
        """ Only bank holidays. Weekends by themselves are not a holiday. """

        m = dt.m
        d = dt.d
        y = dt.y
        day_in_year = self.day_in_year

        if m == 1 and d == 1:  # new year's day
            return True

        if m == 5 and d == 1:  # May day
            return True

        em = easterMondayDay[y - 1901]

        if day_in_year == em - 3:  # Easter Friday holiday
            return True

        if day_in_year == em:  # Easter monday holiday
            return True

        if m == 12 and d == 25:  # Xmas bank holiday
            return True

        if m == 12 and d == 26:  # Xmas bank holiday
            return True

        return False

###############################################################################

    def holiday_none(self, dt=None):
        """ No day is a holiday. """
        return False

###############################################################################

    def get_holiday_list(self, year: float):
        """ generates a list of holidays in a specific year for the specified
        calendar. Useful for diagnostics. """
        start_dt = Date(1, 1, year)
        end_dt = Date(1, 1, year + 1)
        holiday_list = []
        while start_dt < end_dt:
            if self.is_business_day(start_dt) is False and \
                    start_dt.is_weekend() is False:
                holiday_list.append(start_dt.__str__())

            start_dt = start_dt.add_days(1)

        return holiday_list

###############################################################################

    def easter_monday(self,
                      year: float):
        """ Get the day in a given year that is Easter Monday. This is not
        easy to compute, so we rely on a pre-calculated array. """

        if year > 2100:
            raise FinError(
                "Unable to determine Easter monday in year " + str(year))

        em_days = easterMondayDay[year - 1901]
        start_dt = Date(1, 1, year)
        em = start_dt.add_days(em_days-1)
        return em

###############################################################################

    def __str__(self):
        s = self.cal_type.name
        return s

###############################################################################

    def __repr__(self):
        s = self.cal_type.name
        return s

###############################################################################



###############################################################################

class JointCalendar:
    """
    联合日历：将多个日历类型合并，节假日取并集。
    只要任一子日历认为是节假日，则该天为节假日。
    """

    def __init__(self, calendar_types):
        """
        :param calendar_types: CalendarTypes枚举值列表
        """
        if not calendar_types or not all(isinstance(c, CalendarTypes) for c in calendar_types):
            raise FinError("JointCalendar 需要至少一个 CalendarTypes 枚举值")
        
        # 存储子日历对象和类型
        self.calendars = [Calendar(cal_type) for cal_type in calendar_types]
        self.calendar_types = calendar_types
        
        # 添加 value 属性，使其更像 CalendarTypes 枚举值
        self.value = CalendarTypes.JOINT.value
        self.name = "JOINT"

    def is_business_day(self, dt: Date):
        """
        只要有一个子日历不是工作日，则该天不是工作日
        """
        for cal in self.calendars:
            if not cal.is_business_day(dt):
                return False
        return True

    def is_holiday(self, dt: Date):
        """
        只要有一个子日历认为是节假日，则该天为节假日
        """
        for cal in self.calendars:
            if cal.is_holiday(dt):
                return True
        return False

    def adjust(self, dt: Date, bd_type: BusDayAdjustTypes):
        """
        根据业务日调整规则调整日期
        """
        # 创建一个临时 Calendar 对象来处理调整
        temp_cal = Calendar(self)
        return temp_cal.adjust(dt, bd_type)

    def add_business_days(self, start_dt: Date, num_days: int):
        """
        添加指定数量的工作日
        """
        # 创建一个临时 Calendar 对象来处理添加业务日
        temp_cal = Calendar(self)
        return temp_cal.add_business_days(start_dt, num_days)

    def get_holiday_list(self, year: float):
        """
        返回所有子日历的节假日并集（去重，非周末）
        """
        start_dt = Date(1, 1, year)
        end_dt = Date(1, 1, year + 1)
        holiday_list = []
        
        while start_dt < end_dt:
            # 使用联合日历的业务日判断逻辑
            if self.is_business_day(start_dt) is False and start_dt.is_weekend() is False:
                holiday_list.append(start_dt.__str__())
            
            start_dt = start_dt.add_days(1)
        
        return holiday_list

    def __str__(self):
        return "JointCalendar(" + ", ".join([str(c) for c in self.calendar_types]) + ")"

    def __repr__(self):
        return self.__str__()

###############################################################################
