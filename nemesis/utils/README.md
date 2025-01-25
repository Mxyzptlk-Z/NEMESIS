## FinDayCount

The year fraction function can take up to 3 dates, D1, D2 and D3 and a annual_frequency in specific cases. The current day count methods are listed below.

* THIRTY 360 BOND - 30E/360 ISDA 2006 4.16f, German, Eurobond(ISDA 2000)
* THIRTY E 360 - ISDA 2006 4.16(g) 30/360 ISMA, ICMA
* THIRTY E 360 ISDA - ISDA 2006 4.16(h)
* THIRTY E PLUS 360 - A month has 30 days. It rolls D2 to next month if D2 = 31
* ACT ACT ISDA - Splits accrued period into leap and non-leap year portions.
* ACT ACT ICMA - Used for US Treasury notes and bonds. Takes 3 dates and a annual_frequency.
* ACT 365 F - Denominator is always Fixed at 365, even in a leap year
* ACT 360 - Day difference divided by 360 - always
* ACT 365L - the 29 Feb is counted if it is in the date range

