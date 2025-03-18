## In what cases when American option price equal to European option price?

### I. Call option

Let $\tilde C_K(t,T)$ be the value of an American call option with strike $K$ and maturity $T$, and $C_K(t,T)$ the value of a European call option with the same parameters.

For a non-dividend-paying stock, $\tilde C_K(t,T)=C_K(t,T)$

Let's prove it

> **Result**: The European call price on a non-dividend paying stock satisfies
>
> $$
> max(0,S_t-Ke^{-r(T-t)}) \leq C_K(t,T) \leq S_t
> $$

The left inequality can be proven using no-arbitrage argument whereas the right inequality can be proven using intrinsic value formula for European call option.

By equipping ourselves with result above, it is easy to prove the following statement:

> Suppose the American is exercised at $ t<T $, then
>
> $$
> \tilde C_K(t,T) = S_t-K \leq C_K(t,T)
> $$

Indeed, since $e^{-r(T-t)} \leq 1$, so

$$
\tilde C_K(t,T) = S_t - K \leq S_t - Ke^{-r(T-t)} \leq max(0,S_t-Ke^{-r(T-t)}) \leq C_K(t,T)
$$

Q.E.D.

> Alternatively, there's another more elegant proof using put-call parity.
>
> From put-call parity we have $C_t=P_t+S_t-Ke^{-r(T-t)}$, so
>
> $$
> C_t \geq S_t-Ke^{-r(T-t)} > S_t-K
> $$
>
> This means that the price of the call $C_t$ at any time $ 0<t<T $  is always greater than the value of exercising the call which is $S_t-K$. Therefore, the optionality of exercising an American call option (with no dividends) before $T$ has no value.

Note that the proof is done assuming no dividend is paid. In the case of paying dividends, two situations should be considered:

- **Discrete Dividends**: Paid once during the life of the option.
- **Continuous Dividends**: Instead of receiving cash, you receive additional fragmental units of the underlying asset.

In this case, rewrite put-call parity as:

$$
\begin{align*}
\begin{split}
\left \{
\begin{array}{ll}
C_t + Ke^{-r(T-t)} = P_t + S_t - De^{-r\tau}, & discrete\ dividend, \\
C_t + Ke^{-r(T-t)} = P_t + S_te^{-q(T-t)}, & continuous\ dividend \\
\end{array}
\right.
\end{split}
\end{align*}
$$

In both cases $ C_t $ is not necessarily greater than $ S_T - K $, therefore not exercising the option before $ T $ does not guarantee the optimal benefit.

### II. Put option

Similarly, for put options, the optionality of exercising an American call option (w/ or w/o dividends) before $T$ is justified, given the same put-call parity.

$$
P_t = C_t + Ke^{-r(T-t)} - S_t \geq  Ke^{-r(T-t)} - S_t \ngtr K-S_t \ , \quad without\ dividend,
$$

$$
P_t = C_t + Ke^{-r(T-t)} - S_t \geq  Ke^{-r(T-t)} - S_te^{-q(T-t)} \ngtr K-S_t \ , \quad with\ dividend
$$

It's also straightforward to justify that assuming $r=0$, exercising an American put option before $T$ is undesirable.

In this case, the value of an American put option is the same as a Eurepean put option.

---

Here's an idea of what's going on.

The price of a European Call option written for a stock that does not pay dividends is always higher than its intrinsic value. Therefore, in that case, *Prices of European and American Call options are equal*.

Note that this is not true for Put options, since Put values are short interest rates (Calls are long interest rates). If interest rates are zero, American and European Puts have the same price.

Note that you are always better waiting until maturity to exercise the option, if the stock does not pay dividends, since otherwise you will lose time value. When a stock pays dividends it might be better to exercise the day before the stock goes ex-dividend, because the drop in price of the stock may not compensate for the time value.

To put these together, assuming no dividends, European and American Call options have the same price; assuming no interest rates $(r=0)$, the same happens for Puts.
