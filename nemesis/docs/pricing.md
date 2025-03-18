<div align='center'>
    <font size='8'>Asset Pricing Demystified</font>
</div>

# 前言

该篇属于资产定价纯理论系列，全文字数1w+，全部读完预计30分钟，需要读者具有基础的概率论和随机过程知识。本文写作耗时近半年，对现代资产定价的理论体系进行了系统的梳理。虽然内容可能比较枯燥，但耐心看完必定会对资产定价的底层逻辑和发展脉络有更清晰的认识。

作为现代金融理论的基石，资产定价（Asset Pricing）理论在金融学科中占据着核心地位。它致力于解答金融市场中最根本的问题：如何准确、合理地为各类金融资产定价。在实际中，它为投资组合构建、衍生品定价、风险度量等提供了坚实的理论依据。

在初学Black-Scholes公式时，我们经常会听到一个词：“风险中性”。教材一般会说，“我们在风险中性环境下写出它的定价公式”，而至于为什么要在“风险中性环境”下去定价，教材往往一笔带过。那么这里所说的“风险中性”究竟是什么？为什么要在这个测度下评估产品价值而不是其它测度？这篇文章将从最基础的概念开始，一步一步剖析它的原理与底层逻辑，并在这个框架下延伸到挂钩其它标的的衍生品定价中去。

# 引子

在现实世界中，金融产品$V$的价值一般以货币为单位计量，如果以美元为例，我们的目标就是得到$V$在任意时点$t$以$\$$表示的值，记作$V_\$(t)$。

然而，货币本身具有时间价值，其购买力往往随时间推移而递减。这一特性使得以货币为基准来衡量资产价值存在内在的局限性，从而给金融产品的准确定价带来了显著的挑战：货币的时间价值不仅影响了资产价值的表现形式，还潜在地扭曲了不同时期的价值比较。

鉴于上述背景，我们寻求另一种替代性计价单位，即等价物。我们的目标是确定这样一种等价物（numeraire），它能够使资产价值$V$在其度量下展现出更为稳定和可靠的特性，有效消除货币时间价值带来的扭曲。同时，这种理想的等价物应当具有可转换性，即能够方便地与传统货币单位进行互换和表述。

同时，每个等价物对应着一个概率测度（measure），选择不同的等价物等同于在不同的概率空间中描述随机过程。通过巧妙选择适当的等价物（即概率测度），我们可以显著降低问题的复杂度。比如，我们可以将原本需要考虑两个或多个随机变量的问题，转化为仅需考虑一个随机变量的问题。因此，测度变换本质上是一个降维的过程。

以上描述勾勒出了资产定价理论的核心思考路径，为我们引入广泛应用的风险中性定价原理奠定了基础。

# 1. 等价物变换（Change of Numeraire）

现代资产定价理论的一个关键概念是**等价物**（numeraire）的概念。一个资产的价格通常由另一个参考资产表示，这个参考资产也被称作等价物。以两种不同参考资产表示的资产价格之间的关系被称为**等价物变换**。 

等价物的定义是，在所有时间$t$内，价格过程（price process）$\mathcal{N}(t)$使$\mathcal{N}(t)>0$的任何可交易资产。

给定一个资产$X$和两个参考资产$Y$和$Z$，我们可以用以下公式写出$X$相对于参考资产$Y$的价格：

$$ X=X_Y(t)·Y $$

同样，如果我们将$Z$作为一个参考资产，则有：

$$ X=X_Z(t)·Z $$

于是，有**等价物变换公式**（change of numeraire formula）

$$ X=X_Y(t)·Y=X_Z(t)·Z \tag{1} $$

若将$\mathcal{N}(t)$作为等价物，则资产$S$的相对价格过程定义为：

$$S_{\mathcal{N}}(t)=\frac{S(t)}{\mathcal{N}(t)}$$

也就是说，资产的相对价格是以等价物形式表示的价格。

# 2. 套利资产与货币市场账户

如果一个资产的价值随时间保持不变，那么我们说该资产没有**时间价值**（no time value），比如贵金属、在未来某个固定时间交付特定资产的合约。注意不要将无时间价值资产与无时间价值资产的价格的概念混淆。例如，一盎司黄金是一种没有时间价值的资产，它不会随着时间的推移而变化，但这种资产相对于美元的价格可能会随着时间的推移而变化。

当资产价值随时间发生变化时，我们就说该资产具有时间价值（time value）。具有时间价值的资产可能会随着时间的流逝而折价，例如货币、支付股息的股票和大多数消费品。

如果持有某种资产可以创造套利机会，我们就称这种资产为**套利资产**（arbitrage asset）。如果持有某种资产不可能产生套利机会，我们就称这种资产为**无套利资产**(no-arbitrage asset)。有一种简单的方法可以确定给定资产$X$是套利资产还是无套利资产。假设$V$是一份在未来某个时间$T$交割一单位资产$X$的合约，则

$$ V_T =X_T $$

当$V_t=X_t$，$\forall t\leq T$，资产$X$是无套利资产；当$V_t\neq X_t$，对于某些$t\leq T$，资产$X$是套利资产。

货币具有时间价值这一事实意味着，以美元计价的价格在时间上可能并不一致。这就是所谓货币的时间价值：今天的一美元比明天的一美元值钱。因此，当以美元表示资产$S$的价格时，这些价格会有一个向上的倾斜，与参考资产（reference asset）的价值损失相对应。

为了消除参考资产贬值的影响，我们可以用与美元对应的无套利替代资产（如货币市场账户$M$或债券$B^T$）来表示资产$S$的价格。价格$S_M(t)$和$S_{B^T}(t)$被称为资产$S$的**贴现价格**。其中，货币市场的美元价格表示为：

$$ M_{\$}(t)=exp(\int_0^tr(u)du) \tag{2} $$

利用等价物变换公式，同时假设利率为常数，上式又可以写为：

$$ M_t=e^{rt}·{\$}_t $$

如果将(2)式写成微分形式，则有：

$$ dM_{\$}(t)=r(t)M_{\$}(t)dt \tag{3} $$

其中，利率$r(t)$可视为套利资产$\$$相对于无套利资产$M$（货币市场账户）的贬值速度。如果利率$r(t)$是确定的，我们同样可以得到：

$$ B_{\$}^T(t)=exp(-\int_t^Tr(u)du) \tag{4} $$


# 3. 资产定价基本定理（Fundamental Theorems of Asset Pricing）

资产定价基本定理是现代金融理论的基石。它揭示了无套利条件、市场完备性和风险中性定价之间的深刻联系，为我们理解和应用金融数学模型提供了清晰的框架。

资产定价的一般假设是市场不存在套利。如果出现套利机会，市场通常会在短时间内自我修正。显然，整个理论取决于投资组合中的资产一开始就是无套利资产这一事实，否则投资组合就不是无套利的。其中，资产定价理论的核心是资产定价第一基本定理。

**资产定价第一基本定理**

如果存在一个概率测度$\mathbb{P}^Y$，使得价格过程$X_Y(t)$在$\mathbb{P}^Y$测度下是鞅，其中$X$是任意无套利资产，$Y$是任意无套利资产且价格为正，那么市场上就不存在套利。

这个定理的严格证明最早由Harrison和Pliska(1981)在有限的概率空间给出，但一个更简单的方式是利用反证法，这里不做赘述。

值得注意的是，该定理的反向陈述，即无套利条件意味着存在鞅测度$\mathbb{P}^Y$是成立的（至少在经典的数学模型中）。这意味着无套利条件隐含了对于相应的概率测度而言，资产价格是一个鞅的结论。于是，价格过程为鞅是无套利的充要条件，但证明其必要性超出了本文的范畴。在实际应用中，我们只需从价格的鞅演化过程出发即可。

该定理指出，在合适的测度下，价格过程是一个鞅，因此它的期望值不随时间而变化：

$$ V_Y(t)=\mathbb{E}_t^Y[V_Y(T)] \tag{5} $$

其中，$V$和$Y$是两个无套利资产，上式等价于

$$ V=\mathbb{E}_t^Y[V_Y(T)]·Y \tag{6} $$

当计价资产$Y$是到期日为$T$的债券$B^T$时，相应的$\mathbb{P}^T$测度称为**T-远期测度**（T-forward measure）；当基础资产是货币市场账户$M$时，相应的$\mathbb{P}^M$测度则称为**风险中性测度**（risk-neutral measure）。当利率变化是确定性的（deterministic），风险中性测度与T-远期测度是一致的。

需要注意的是，对于以货币结算的合约，我们一般选择T-远期测度，因为它同样适用于随机利率的情况；而只有在利率是确定的情况下，风险中性测度才可用于此类合约的定价。由于美元是一种套利资产，因此不存在与将美元作为参考资产相对应的鞅测度$\mathbb{P}^\$$ 。其他无套利参考资产都有自己的鞅测度，如当标的参考资产是股票$S$时，相应的$\mathbb{P}^S$测度称为**股票测度**（stock measure）。

那么该如何确定资产的货币价格呢？

由于美元是一种套利资产，因此当使用美元作为参考资产时，资产定价第一基本定理并不适用。资产的美元价格必须根据等价物变换公式(1)计算：

$$ V_{\$}(t)=V_Y(t)·Y_{\$}(t) $$

若使用在$T$时刻到期的债券$B^T$作为参考资产，根据资产定价第一基本定理:

$$ V_{B^T}(t)=\mathbb{E}_t^T[V_{B^T}(T)] $$

通过等价物转换公式，将上式转换为美元价格，同时注意到$B_\$^T(T)=1$，于是我们可以写成：

$$ V_{\$}(t)=V_{B^T}(t)·B^T_{\$}(t)=\mathbb{E}_t^T[V_{\$}(T)·{\$}_{B^T}(T)]·B^T_{\$}(t)=\mathbb{E}_t^T[V_{\$}(T)]·B^T_{\$}(t) $$

因此，我们有：

$$ V_{\$}(t)=B^T_{\$}(t)·\mathbb{E}_t^T[V_{\$}(T)] \tag{7} $$

公式(7)在目前衍生品定价的框架中具有重要意义。其优势在于，通过使用相应的T-远期测度，我们可以立即获得给定未定权益（contingent claim）的美元价值。注意到公式中并不包含利率$r(t)$，如果我们假定债券价格与利率有一定的关系，那么它只会间接地出现在债券价格$B^T_\$(t)$中。然而，我们往往不需要进行这一步，因为债券价格$B^T_\$(t)$可以直接从市场报价得到。

另一个可以选择的美元无套利替代资产是货币市场账户$M$。与零息债类似，有：

$$ V_{\$}(t)=V_M(t)·M_{\$}(t)=\mathbb{E}_t^M[V_{\$}(T)·{\$}_M(T)]·M_{\$}(t) $$

根据(2)，上式又可以写成：

$$ V_{\$}(t)=\mathbb{E}_t^M[exp(-\int^T_tr(s)ds)·V_{\$}(T)] \tag{8} $$

公式(8)指出，**未定权益$V$的价格是其在风险中性测度下的贴现报酬的期望**。一些教材将这个等式作为衍生品定价的起点，但这种方法只有在利率$r$是确定性的情况下才能放心使用。当利率过程$r(t)$是随机的（现实市场中的典型情况），期望值中出现的随机变量$exp(-\int^T_tr(s)ds)$和$V_\$(T)$可能是相关的，此时对未定权益$V$的定价就必须解决$exp(-\int^T_tr(s)ds)$和$V_\$(T)$的联合分布问题。这个问题非常繁琐，特别是当$V$本身是一个利率产品时。

当利率是确定性的，折现因子$exp(-\int^T_tr(s)ds)$也是确定性的，并且与回报$V_\$(T)$相独立，于是可以将其从(8)的期望值中提取出来：

$$ V_{\$}(t)=exp(-\int^T_tr(s)ds)·\mathbb{E}_t^M[V_{\$}(T)] $$

在此情景下，我们注意到$B_\$^T(t)=exp(-\int^T_tr(s)ds)$，因此公式(7)变为：

$$ V_{\$}(t)=exp(-\int^T_tr(s)ds)·\mathbb{E}_t^T[V_{\$}(T)] \tag{9} $$

这意味着

$$ \mathbb{E}_t^M[V_{\$}(T)]=\mathbb{E}_t^T[V_{\$}(T)] $$

也就是说，T-远期测度$\mathbb{P}^T$与风险中性测度$\mathbb{P}^M$是等价的，但仅限于利率是确定性的情况。

同时注意到，如果将(8)中的$V$取作零息债$B^T$，我们有：

$$ B^T_{\$}(t)=\mathbb{E}_t^M[exp(-\int^T_tr(s)ds)·B^T_{\$}(T)]=\mathbb{E}_t^M[exp(-\int^T_tr(s)ds)] $$

现在我们终于可以区分零息债和折现因子之间的关系了：

- 在非随机利率假设下，零息债价格和折现因子是一样的；
- 在随机利率假设下，零息债价格是折现因子在风险中性测度下的期望。

到此为止，资产定价第一基本定理表明了无套利条件等价于存在至少一个风险中性测度；而资产定价第二基本定理进一步指出，如果市场是完备的，那么这个风险中性测度是唯一的。

**资产定价第二基本定理**

在一个完备市场中（任何衍生证券都可以用基础资产复制），存在唯一的鞅概率测度（也称为等价鞅测度）。

在衍生品定价中，这个定理保证了我们可以使用唯一的风险中性测度来计算期望值，从而得到唯一的理论价格。同时，它也解释了为什么Black-Scholes模型等定价公式可以不依赖投资者的风险偏好。

需要注意的是，现实中我们经常遇到不同的测度，如风险中性测度、T-forward测度、annuity测度等，这似乎与第二基本定理中鞅概率测度唯一性的说法相矛盾。然而，这些不同的测度实际上是基于不同等价物的鞅测度，即每种测度都使特定资产（作为numeraire）的折现价格过程成为鞅。这些不同的测度实际上是相互等价的，它们之间可以通过Radon-Nikodym导数进行转换。因此，第二基本定理中的“唯一性”指的是：对于给定的numeraire，存在唯一的等价鞅测度。

# 4. 测度变换（Change of Measure）

如前节所述，选择测度相当于选择等价物，由不同等价物所隐含的概率测度之间的关系由拉东-尼科迪姆导数（Radon-Nikodym Derivative）来描述。

假设$X$是一个无套利参考资产，$Y$是另一个无套利参考资产，$V$是待定价资产。根据公式(6)，我们有：

$$ V=\mathbb{E}^Y[V_Y(T)]·Y=\mathbb{E}^X[V_X(T)]·X $$

原则上，我们可能有无限多个不同的概率测度$\mathbb{P}^Y$和$\mathbb{P}^X$，但是对于任意的未定权益$V$来说，R-N导数将测度$\mathbb{P}^Y$和$\mathbb{P}^X$联系了起来，使得其在不同测度下的定价在同一价格水平。

直观上，$\mathbb{P}^Y$和$\mathbb{P}^X$两个测度由一个缩放因子$\mathbb{Z}(T)$联系起来：

$$ \mathbb{E}^Y[V_X(T)·\mathbb{Z}(T)]=\mathbb{E}^X[V_X(T)] \tag{10} $$

将上式写作积分形式：

$$ \int_{\Omega}V_X(T,\omega)\mathbb{Z}(T,\omega)d\mathbb{P}^Y(\omega)=\int_{\Omega}V_X(T,\omega)d\mathbb{P}^X(\omega) $$

对于任意的可积随机变量$V_X(T,\omega)$均成立，于是我们得到以下$\mathbb{Z}(T)$的表示：

$$ \mathbb{Z}(T)=\frac{d\mathbb{P}^X}{d\mathbb{P}^Y} \tag{11} $$

换句话说，

$$ \mathbb{P}^X(A)=\int_A\mathbb{Z}(T,\omega)d\mathbb{P}^Y(\omega), \quad A\in\mathcal{F} \tag{12} $$

直观地说，这表示在$\mathbb{P}^Y$测度下，事件$\omega$概率的权重必须增加或减少多少，才能得到与使用$\mathbb{P}^X$测度相同的结果。缩放因子$\mathbb{Z}(T)$被称作**Radon-Nikodym derivative**。当结果空间$\Omega$是离散的，式(12)可以被写为：

$$ \mathbb{P}^X(\omega)=\mathbb{Z}(T,\omega)·\mathbb{P}^Y(\omega), \quad \omega\in\Omega $$

类似地，我们也可以考虑测度变化的倒数：

$$ \frac{1}{\mathbb{Z}(T)}=\frac{d\mathbb{P}^Y}{d\mathbb{P}^X} $$

这意味着

$$ \mathbb{E}^Y[V_Y(T)]=\mathbb{E}^{X}\bigg[\frac{V_Y(T)}{\mathbb{Z}(T)}\bigg] $$

Radon-Nikodym导数有以下金融含义：

$$ \mathbb{E}^X[V_X(T)]·X_0=\mathbb{E}^Y[V_X(T)·\mathbb{Z}(T)]·X_0=\mathbb{E}^Y[V_Y(T)]·Y_0 $$

其中，第一个等式源于测度转换公式，第二个等式源于等价物转换公式。由于这个恒等关系对于任意未定权益$V$都是成立的，我们有：

$$ [V_X(T)·\mathbb{Z}(T)]·X_0=[V_Y(T)]·Y_0 $$

即

$$ \mathbb{Z}(T)=\frac{d\mathbb{P}^X}{d\mathbb{P}^Y}=\frac{X_Y(T)}{X_Y(0)} $$

注意到上式对于资产X和Y是对称的，即

$$ \frac{1}{\mathbb{Z}(T)}=\frac{d\mathbb{P}^Y}{d\mathbb{P}^X}=\frac{Y_X(T)}{Y_X(0)} $$

在上一节中我们证明了当利率是确定的，风险中性测度$\mathbb{P}^M$与$T$-远期测度$\mathbb{P}^T$是一致的。R-N导数可以用来检查这一结论：

$$ \mathbb{Z}(T)=\frac{d\mathbb{P}^M}{d\mathbb{P}^T}=\frac{M_{B^T}(T)}{M_{B^T}(0)}=\frac{M_{\$}(T)·{\$}_{B^T}(T)}{M_{\$}(0)·{\$}_{B^T}(0)}=\frac{exp\big(\int_0^Tr(t)dt\big)·1}{1·exp\big(\int_0^Tr(t)dt\big)}=1 $$

它隐含了对于可测集$A$，有：

$$ \mathbb{P}^M(A)=\int_A\mathbb{Z}(T,\omega)d\mathbb{P}^T(\omega)=\int_A1d\mathbb{P}^T(\omega)=\mathbb{P}^T(A), \quad A\in\mathcal{F} $$

结论得证。

以上是在$t=0$时刻对R-N导数的描述，我们可以进一步泛化这一概念到任意$t(t\leq T)$时刻（条件期望的R-N导数），根据等价物变换公式，我们有：

$$ \mathbb{E}_t^X[V_X(T)]·X_t=\mathbb{E}_t^Y[V_Y(T)]·Y_t=\mathbb{E}_t^Y[V_X(T)·X_Y(T)]·Y_t $$

对上式进行等价变化：

$$ \mathbb{E}_t^X[V_X(T)]=\mathbb{E}_t^Y\bigg[V_X(T)·\frac{X_Y(T)}{X_Y(t)}\bigg]=\mathbb{E}_t^Y\bigg[V_X(T)·\frac{\mathbb{Z}(T)}{\mathbb{Z}(t)}\bigg] $$

将其转换为R-N导数表示，便可得到我们熟悉的**Bayes公式**：

$$ \mathbb{E}_t^X[V_X(T)]=\frac{1}{\mathbb{Z}(t)}·\mathbb{E}_t^Y[V_X(T)·\mathbb{Z}(T)] \tag{13} $$

# 5. 连续时间过程（Continuous Time）

现在，让我们先暂停一下，整理一下我们现有的理论工具：资产定价第一基本定理告诉我们，如果市场是无套利的，那么存在一个测度，使得任意可交易资产的相对价格过程是鞅；资产定价第二基本定理又告诉我们，如果市场是完备的，那么这个测度唯一；同时，Radon-Nikodym导数为我们提供了一般的测度变换框架。

于是我们解决问题的路径就很明朗了：找到这个测度$\rightarrow$证明市场的完备性$\rightarrow$通过R-N导数变换测度，一切水到渠成。

现在让我们来找到这个测度。回到我们最开始的目标：通过选择合适的测度来降低问题的复杂度，那么如何才能实现降维的目的呢？在金融数学中，我们通常使用**扩散过程**（diffusion process）描述资产价格的变化路径，这个随机过程一般由漂移项（drift）和随机项（Brownian motion）组成：

$$ dS(t)=a(S,t)dt+b(S,t)dW \ \ with\ \ dW～\phi\sqrt{dt}, \  \phi～N(0,1) \tag{14} $$

记$U(S,t)$是一个以$S$作为底层资产的可交易（tradable）金融产品，那么根据**伊藤引理**（Ito's lemma），在真实世界中$U$的价格过程为：

$$ 
\begin{gather*}
dU(S,t)=a_U(S,t)dt+\frac{\partial{U}}{\partial{S}}b(S,t)dW \\
where \quad a_U(S,t):=\frac{\partial{U}}{\partial{S}}a(S,t)+\frac{\partial{U}}{\partial{t}}+\frac{1}{2}\frac{\partial^2{U}}{\partial{S^2}}b(S,t)^2 \tag{15}
\end{gather*}
$$

更进一步，选择一个任意的可交易资产$Y$作为等价物资产。注意到等价物资产$Y$的选择并不是完全随机的，如果我们假设市场只由一个单一的随机因素驱动（one-factor model），也就是布朗运动$dW$，此时如果$Y$也存在随机项，那么它必须由与$S$相同的随机游走过程支配；否则这个模型被称为多因素模型（multifactor model）。与式(14)类似，描述等价物资产$Y$的通用价格过程满足：

$$ dY(t)=m(Y,t)dt+n(Y,t)dW \ \ with\ \ dW～\phi\sqrt{dt}, \  \phi～N(0,1) \tag{16} $$

其中，$m$和$n$为可料过程，随机游走$dW$与驱动标的资产价格过程$S(t)$的随机项一致。

如果我们选用恰当的测度使得$U$相对于参考资产$Y$的价格过程的漂移项为零，那么$U$的相对价格是一个鞅，这样就大大简化了计算的过程。它隐含了在这个测度下，相对价格过程有如下形式：

$$
\begin{gather*}
U_Y(t)=\mathbb{E}_t^Y[U_Y(s)], \quad \forall s\geq t \tag{17} \\
dU_Y(t)=\widetilde{g}_U(S,t)\widetilde{dW} \tag{18}
\end{gather*}
$$

其中，$\widetilde{dW}$是一个**布朗运动**（Brownian motion），$\widetilde{g}_U$是一个**可料过程**（previsible process），且对于每个资产均不同。

于是我们的目标可以细化为：寻找一个概率测度，使得所有可交易资产按照等价物资产$Y$计价的相对价格均为鞅。现在我们与这个目标之间还存在着一条鸿沟（理论的缺失），但是我们可以从一个短期目标开始，分而治之：找到一个概率测度，使得一个单一资产$U$的相对价格

$$ Z(S,t):=\frac{U(S,t)}{Y(t)} \tag{19} $$

是一个鞅。根据**乘法原理**（product rule），$Z$的价格过程可以建立为：

$$ dZ=d\big[Y^{-1}U\big]=Ud\big[Y^{-1}\big]+Y^{-1}dU+dUd\big[Y^{-1}\big] \tag{20} $$

其中，微分$dU$已经由式(15)定义，$f(Y):=Y^{-1}$的微分通过应用伊藤引理获得，将$\frac{\partial{f}}{\partial{Y}}=-\frac{1}{Y^2}$，$\frac{\partial^2{f}}{\partial{Y^2}}=\frac{2}{Y^3}$和$\frac{\partial{f}}{\partial{t}}=0$代入式(15)，可得：

$$ d\big[Y^{-1}\big]=\bigg[-\frac{1}{Y^2}m+\frac{1}{Y^3}n^2\bigg]dt-\frac{1}{Y^2}ndW $$

注意到式(20)的最后一项是两个随机微分方程相乘，包含了$dt$和$dW$的高阶项，同时应用$(dW)^2\approx{dt}$，有：

$$
\begin{align*}
dUd\big[Y^{-1}\big]&=\bigg(a_Udt+\frac{\partial{U}}{\partial{S}}bdW\bigg)\frac{1}{Y^2}\big(\big[-m+n^2/Y\big]dt-ndW\big) \\
&=-\frac{\partial{U}}{\partial{S}}b\frac{n}{Y^2}\underbrace{(dW)^2}_{dt}+\mathcal{O}(dtdW)
\end{align*}
$$

将以上每个部分代入式(20)，可以得到$dZ$的表达式：

$$
\begin{align*}
dZ&=\frac{U}{Y}\bigg(\bigg[\frac{n^2}{Y^2}-\frac{m}{Y}\bigg]dt-\frac{n}{Y}dW\bigg)+\frac{a_U}{Y}dt+\frac{\partial{U}}{\partial{S}}\frac{b}{Y}dW-\frac{\partial{U}}{\partial{S}}\frac{bn}{Y^2}dt \\
&=\bigg(\frac{b}{Y}\frac{\partial{U}}{\partial{S}}-\frac{n}{Y}\frac{U}{Y}\bigg)dW+\bigg(\frac{a_U}{Y}+\bigg[\frac{n^2}{Y^2}-\frac{m}{Y}\bigg]\frac{U}{Y}-\frac{bn}{Y^2}\frac{\partial{U}}{\partial{S}}\bigg)dt \\
&=\bigg(\frac{b}{Y}\frac{\partial{U}}{\partial{S}}-\frac{n}{Y}\frac{U}{Y}\bigg)\Bigg\{dW+\frac{a_U+\big[\frac{n^2}{Y^2}-\frac{m}{Y}\big]U-b\frac{n}{Y}\frac{\partial{U}}{\partial{S}}}{b\frac{\partial{U}}{\partial{S}}-n\frac{U}{Y}}dt\Bigg\} \tag{21}
\end{align*}
$$

其中，$dW$项前的系数被强制当作因子提取出来。回想我们的目标：寻找一个概率测度，使得$Z$是一个鞅。换句话说，一个如式(18)形式的随机过程。

令

$$ d\widetilde{W}:=dW+\frac{a_U+\big[\frac{n^2}{Y^2}-\frac{m}{Y}\big]U-b\frac{n}{Y}\frac{\partial{U}}{\partial{S}}}{b\frac{\partial{U}}{\partial{S}}-n\frac{U}{Y}}dt \tag{22} $$

如果测度$d\widetilde{W}$存在，且是一个标准布朗运动，也就是

$$ d\widetilde{W}～\phi\sqrt{dt} \quad with \quad \phi～N(0,1) $$

那么随机过程$dZ$就变成了我们设想的形式（漂移项为0，随机项是布朗运动）。这就引出了著名的**Girsanov定理**，它具体化了R-N框架在布朗运动环境下的应用。

**Cameron-Martin-Girsanov定理**

假设$W(t)$是关于概率测度$\mathcal{P}$的布朗运动，$\gamma(t)$是一个可料过程（previsible process），它对于某个未来时间$T$满足有界性条件（Novikov condition）：

$$ \mathbb{E}_{\mathcal{P}}\bigg[exp\bigg(\frac{1}{2}\int_0^T\gamma^2(t)dt\bigg)\bigg]<\infty $$

那么存在一个测度$\mathcal{Q}$与测度$\mathcal{P}$等价，使得

$$ \widetilde{W}_t=W_t+\int_0^t\gamma(s)ds $$

是一个关于测度$\mathcal{Q}$的布朗运动。其中，测度$\mathcal{P}$与$\mathcal{Q}$之间的转换关系由Radon-Nikodym导数定义：

$$ \frac{d\mathcal{Q}}{d\mathcal{P}}=exp\bigg(-\int_0^t\gamma(s)dW_s-\frac{1}{2}\int_0^t\gamma^2(s)ds\bigg) $$

可以看到，Girsanov定理给出了对标准布朗运动进行整体上的平移后，RN导数应该满足什么样的形式才能使得新测度$\mathcal{Q}$下平移后的过程依旧是布朗运动。其中，Novikov条件的本质是为了保证$\rho_t=\frac{d\mathcal{Q}}{d\mathcal{P}}$是一个鞅，也就是$E[\rho_t]=1$，即保证$\mathcal{Q}$是一个概率测度。在大部分情况下，Novikov条件都能被满足。

简单来说，Radon-Nikodym导数提供了从实际概率测度到风险中性测度转换的一般框架。而Girsanov定理具体说明了如何在连续时间模型中实现这种转换，特别是在处理带有漂移项的随机微分方程时。

为了应用该定理，我们将式(22)中$dt$前的系数识别为Girsanov定理中的$\gamma(t)$。首先，这个系数只取决于在$t$时刻已知的变量，因此在$t$时刻它是确定的（可料的）。接着，假设定理中的有界性条件也得到满足（在我们的模型中总是如此），那么定理表示测度$d\widetilde{W}$是一个布朗运动。式(21)中的$dZ$可以写成式(18)中的形式：

$$ \widetilde{g}_Z(S,t)=\frac{b}{Y}\frac{\partial{U}}{\partial{S}}-\frac{n}{Y}\frac{U}{Y} \tag{23} $$

现在我们可以放心地说，$dZ$是一个鞅，与之对应的测度$d\widetilde{W}$是一个鞅测度。

根据上面的推导，我们已经实现了最初定下的短期目标：对于所选的资产$U$，其相对价格是一个鞅，唯一的要求是$U$必须是可交易的。因此，对于任意一个可交易资产（以$S$作为标的资产），都存在一个鞅测度，这个测度（在我们当前的讨论范围内）对于每一个资产$U$都是不同的。换句话说，它取决于我们所选取的$U$。接下来我们需要证明的是每一个可交易资产的相对价格在同一个概率测度下都是一个鞅。在离散时间的设定下，关键是证明一个由$U$和$Y$组成的投资组合所构建的自融资策略能够完全复制$V$；但是对于连续时间的情况，我们需要利用到随机分析中的另一个重要的定理。

**鞅表示定理（Martingale representation）**

如果$Z$是相对概率测度$\mathcal{P}$的一个鞅，其波动率以概率$1$几乎处处非零，也就是说，如果$Z$服从一个随机过程，满足

$$ dZ=b_Z(t)dW \quad with \quad P[b_Z(t)\neq 0]=1, \; \forall t $$

其中，$b_Z(t)$是一个可料过程。如果在这个测度下存在另一个鞅$X$，那么存在一个可料过程$\alpha(t)$，使得

$$ dX=\alpha(t)dZ $$

等价地，以积分形式表示为：

$$ X(t)=X(0)+\int_0^t\alpha(s)dZ(s) $$

过程$\alpha(t)$是唯一的。更进一步，$\alpha$和$b_Z$共同满足有界条件

$$ E\bigg[exp\bigg(\frac{1}{2}\int_0^T\alpha(t)^2b_Z(t)^2dt\bigg)\bigg]<\infty $$

该定理直观地指出，如果波动率不为零，两个鞅过程最多只相差一个可料过程。这隐含了任何一个鞅过程都可以被另一个鞅过程和一个可料过程表示。

然而，在我们的测度下目前只有一个鞅，也就是$U$的相对价格过程$Z$。为了能够应用这一定理，我们需要另一个鞅。由于我们希望得到另一个任意的金融资产$V$的价格信息，我们需要根据$V$来构建第二个鞅。我们可以借助另一个简单的定理来做到这一点：

**Tower Law**

对于任意取决于未来某个时点$T>t$前发生的事件的函数$V$，对于任意概率测度$\mathcal{P}$，$V(T)$在时点$t$的期望

$$ E(t):=E_t^{\mathcal{P}}[V(T)] $$

在概率测度$\mathcal{P}$下是一个鞅，也就是

$$ E(t)=E_t^{\mathcal{P}}[E(u)], \quad \forall u>t $$

将$E$的定义代入$E(t)$是一个鞅的表述中，

$$ E_t^{\mathcal{P}}[V(T)]=E_t^{\mathcal{P}}\big[E_u^{\mathcal{P}}[V(T)]\big], \quad \forall u>t \tag{24} $$

该定理表示，取$u$时刻的期望，然后取该期望值在更早时刻$t$的期望值，得到的结果与直接取更早时刻$t$的期望值相同。

对于一个到期日为$T$的金融资产$V$，其在到期日的损益（payoff profile）$V(T)$只取决于$T$时刻前发生的事件（标的资产$S$的价值）。Tower Law告诉我们，这个损益的期望对于每一个测度而言都是一个鞅，尤其是对于式(19)中$Z$的鞅测度。因此，我们已经在这个测度下找到了两个鞅过程，分别是$Z(t)$和$E_t^Y[V(T)]$。

但是，我们想更进一步，让$V(t)$的相对价格过程本身是一个鞅，而不仅是$V(t)$的期望。因此，相较于考虑$V$本身，我们转而考虑以$Y$计价的相对损益$V(T)/Y(T)$。根据Tower Law，这个函数在$t$时刻的期望（在$Z$的鞅测度下）

$$ E(t):=E_t^Y\bigg[\frac{V(T)}{Y(T)}\bigg] $$

也是一个鞅，我们在下面将其记作$E(t)$。此外，$V$在到期日$t=T$的损益被$Y(t)E(t)$完全复制：

$$ Y(T)E(T)=Y(T)E_T^Y\bigg[\frac{V(T)}{Y(T)}\bigg]=Y(T)\frac{V(T)}{Y(T)}=V(T) \tag{25} $$

现在我们可以清晰地看到，应该如何应用鞅表示定理来构建**复制投资组合**（replicating portfolio）：问题中的鞅是相对价格的期望$E(t)$，第二个鞅是式(19)中我们最初选取的资产$U$的相对价格$Z(t)$。根据鞅表示定理，（如果$Z$的波动率总是非负），那么过程$E(t)$与过程$Z(t)$之间最多相差一个可料过程$\alpha(t)$：

$$ dE=\alpha(t)dZ \tag{26} $$

现在我们利用这个可料过程去构建一个包含$\alpha(t)$个单位的资产$U$以及$\beta$个单位的计价资产$Y$的投资组合。这总是可能的，因为根据鞅表示定理，$\alpha(t)$是可料的，且$U$和$Y$均是可交易的。

$$ \Pi(t)=\alpha(t)U(t)+\beta(t)Y(t) \tag{27} $$

对于所有$t\leq T$的时间，这个组合的价值都应该等于$Y(t)E(t)$，因为根据式(25)，它在到期时（即$t=T$时）准确地复制了$V$的损益。从这个条件中，我们可以推导出构建复制投资组合所需计价资产数量$\beta(t)$：

$$
\begin{align*}
Y(t)E(t)&=\Pi(t)=\alpha(t)U(t)+\beta(t)Y(t) \\
\Leftrightarrow \\
\beta(t)&=E(t)-\alpha(t)\frac{U(t)}{Y(t)}=E(t)-\alpha(t)Z(t) \tag{28}
\end{align*}
$$

这样，我们就确定了复制投资组合的存在。剩下需要证明的是，这个投资组合是**自融资**（self-financing）的，因为只有在衍生工具的整个生命周期内不需要注入或提取资本，我们才能推导出投资组合的价值与金融资产$V$的价值相等。

为此，我们考虑投资组合价值的总变化：

$$
\begin{align*}
d\Pi&=d(YE) \\
&=EdY+YdE+dEdY \\
&=EdY+Y\alpha dZ+\alpha dZdY \\
&=[\beta +\alpha Z]dY+\alpha YdZ+\alpha dZdY \\
&=\alpha[ZdY+YdZ+dZdY]+\beta dY \\
&=\alpha d\underbrace{(ZY)}_U+\beta dY
\end{align*}
$$

其中，第二个等式应用了随机过程的**乘法原理**（stochastic product rule）;第三个等式应用了式(26)的鞅表示定理；第四个等式应用了式(28)的结论；最后一个等式又逆向应用了乘法原理。这个等式表明，式(27)所定义的投资组合价值的总变化完全来自于资产$U$和$Y$的价值变化，而不是头寸$\alpha$和$\beta$的任何调整：

$$ d\Pi(t)=\alpha(t)dU(t)+\beta(t)dY(t) $$

因此，投资组合是自融资的。根据构造，投资组合的价值在任何时候都是$\Pi(t)=Y(t)E(t)$。根据式(25)，它在$T$时刻完全复制了损益$V(T)$，因此在之前的所有时刻，投资组合的价值也必须与衍生品的价值都是相等的：

$$ V(t)=\Pi(t)=Y(t)E(t)=Y(t)E_t^Y\bigg[\frac{V(T)}{Y(T)}\bigg] \tag{29} $$

也就是

$$ \frac{V(t)}{Y(t)}=E_t^Y\bigg[\frac{V(T)}{Y(T)}\bigg] \tag{30} $$

因此，可交易金融资产$V$的相对价格在与使金融资产$U$的相对价格成为鞅的相同的概率测度下也是一个鞅。由于$V$是任意选取的，这意味着所有可交易金融资产的相对价格都是相对于同一概率测度的鞅。

到此为止，我们已经实现了我们的目标，即证明所有可交易金融资产的相对价格$V/Y$相对于$Z=U/Y$的鞅测度都是鞅。剩下的唯一问题是这个测度是否是唯一的，还是可能存在多个这样的测度。为了回答这个问题，我们应用随机分析中的另一个定理，该定理指出：对于完全市场，上面得到的鞅测度是唯一的。

**Harrison-Pliska**

由金融资产和一个计价资产组成的市场是无套利的，当且仅当存在一个与真实世界测度等价的测度，在这个测度下，所有金融资产相对于计价资产的价格都是鞅。这个测度是唯一的，当且仅当市场是完备的。

具体证明过程见参考文献[5]。注意到它实际上是FTAP I和FTAP II的结合。

**总结**

此处我们对理论框架的梳理也到了尾声，让我们总结一下连续时间框架下资产定价理论的核心内容：

- 我们选择一个可交易的金融资产Y作为计价单位（numeraire），以及另一个以$S$为标的的可交易金融资产$U$（如果$S$本身可交易，可以直接选择$S$）。
- 然后，我们找到使$Z=U/Y$成为鞅的概率测度。Girsanov定理保证，只要满足一个技术性的有界条件，通过适当的漂移变换总是可以做到这一点。
- 鞅表示定理和Tower Law使我们能够构建一个由$U$和$Y$组成的自融资投资组合，该组合在到期时可以复制任何以$S$为标的的可交易金融资产$V$的损益结构。这个复制组合的价值由式(29)给出，其中期望是相对于$Z=U/Y$的鞅测度计算的。
- 如果市场无套利，这个复制组合的价值在到期前的任何时间都必须等于衍生品$V(t)$的价值。这意味着，根据式(30)，相对于$Z$的鞅测度，相对价格$V/Y$同样是一个鞅。因此，一旦我们（通过Girsanov）获得了$Z$的鞅测度，所有其他可交易金融资产的相对价格$V/Y$相对于这个相同的测度也都是鞅。
- 最后，Harrison-Pliska定理指出，在完备市场中，这个测度是唯一的：在完备市场中，对于每个计价资产，存在唯一的一个测度，使得所有用这个计价资产计价的可交易资产都是鞅。

这些概念共同构成了现代金融理论的基础，特别是在衍生品定价和风险管理领域。它们提供了一个数学框架，使我们能够在连续时间setting下得到一个金融资产的公允价值。

# 6. Black-Scholes公式

那么如何灵活地运用测度转换和鞅的良好性质呢？下面我们以推导BS公式为例，来说明这些理论给我们带来的便利。

对于Black-Scholes公式，主流的推导方法包括两种：

- 第一种方法是构建一个动态对冲（Dynamic Delta Hedge, DDH）的投资组合，利用无套利原理推出Black-Scholes PDE，然后解一个热方程（heat equation）。这里可能需要用到复杂的换元法，或是直接运用Feynman-Kac公式把解转换为期望的形式，这时候正是风险中性测度下的鞅表示。这类方法是最主流的，也是最好理解的方法。

- 第二种方法是运用测度变换把资产价格映射成一个鞅，然后利用鞅的性质去推导定价公式。接着用暴力积分法或者二次测度变换的技巧直接计算期权的价格。这里我们主要介绍二次测度变换的方法，这是目前为止最简单的方法，不需要任何的求导或积分运算。

- 除此之外还有二叉树极限法、格林函数法、Fokker-Planck方程等比较冷门的方法。

假设真实测度$\mathcal{P}$下，股价$S_t$服从几何布朗运动：

$$ dS_t=\mu S_tdt+\sigma S_tdW_t \tag{31} $$

同时，考虑货币市场账户$M_t$作为计价单位：

$$ dM_t=r_tM_tdt \quad or \quad M_t=e^{rt} \tag{32} $$

对于风险资产的折现价格$\widetilde{S_t}=\frac{S_t}{M_t}$，应用伊藤引理：

$$ \frac{d\widetilde{S_t}}{\widetilde{S_t}}=(\mu-r)dt+\sigma dW_t=\sigma \bigg(dW_t+\frac{\mu-r}{\sigma}dt\bigg) \tag{33} $$

根据Girsanov定理，取$\theta=\frac{\mu-r}{\sigma}$（这就是我们常说的风险溢价，或夏普比率），则式(33)括号中的式子就变成了一个在货币计价单位测度$\mathcal{Q}$下的布朗运动：

$$ \widetilde{W_t}=W_t+\theta t \tag{34} $$

于是在测度$\mathcal{Q}$下，

$$ \frac{d\widetilde{S_t}}{\widetilde{S_t}}=\sigma d\widetilde{W_t} \tag{35} $$

将这个新的测度下的布朗运动$d\widetilde{W_t}$代回式(33)，即可得到标的价格在风险中性测度下的表达式：

$$ \frac{dS_t}{S_t}=rdt+\sigma \widetilde{dW_t} \tag{36} $$

也就是说，在真实测度下，无论证券的风险溢价是多少，它在风险中性测度下总是可以被消除，因而我们能够忽略单一证券的回报特征$\mu$。

根据式(8)，一个欧式看涨期权在$t$时刻的价格可以表示为：

$$ C(0)=e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[max\big(S_T-K,0\big)\big] \tag{37} $$

我们对其进行拆分，

$$
\begin{align*}
C(0)&=e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[max\big(S_T-K,0\big)\big] \\
&=e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[\big(S_T-K\big)\mathbb{1}_{S_T \geq K}\big] \\
&=e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[S_T\mathbb{1}_{S_T \geq K}\big]-Ke^{-rT}\mathbb{E}^{\mathcal{Q}}\big[\mathbb{1}_{S_T \geq K}\big] \\
&=e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[S_T\mathbb{1}_{S_T \geq K}\big]-Ke^{-rT}\mathcal{Q}(S_T\geq K) \tag{38}
\end{align*}
$$

考虑股票的对数收益率

$$ ln\frac{S_T}{S_0}～N\bigg(\big(r-\frac{\sigma^2}{2}\big)T, \; \sigma^2T\bigg) \tag{39} $$

于是式(38)的右半部分可以表示为：

$$ \mathcal{Q}(S_T\geq K)=N(d_2) \tag{40} $$

对于式(38)形式较为复杂的左半部分，我们考虑再进行一次测度变换，将以$M_t$为底的$\mathcal{Q}$空间降到以$S_t$为底的$\mathcal{Q_S}$空间（股票测度）：

$$ e^{-rT}\mathbb{E}^{\mathcal{Q}}\big[S_T\mathbb{1}_{S_T \geq K}\big]=S_0\mathbb{E}^{\mathcal{Q}}\bigg[\frac{e^{-rT}S_T}{S_0}\mathbb{1}_{S_T \geq K}\bigg]=S_0\mathcal{Q_S}(S_T \geq K) \tag{41} $$

其中，二次测度变换的R-N导数为：

$$ \frac{d\mathcal{Q_S}}{d\mathcal{Q}}=\frac{S_t}{S_0}/\frac{M_t}{M_0}=\frac{e^{-rt}S_t}{S_0}=e^{-\frac{1}{2}\sigma^2t+\sigma\widetilde{W_t}} $$

根据Girsanov定理，我们有了一个在$\mathcal{Q_S}$测度下的布朗运动：

$$ \widehat{W_t}=\widetilde{W_t}-\sigma t \tag{42} $$

于是股票价格服从的随机过程在$\mathcal{Q_S}$测度下由式(36)变为：

$$
\begin{align*}
\frac{dS_t}{S_t}&=rdt+\sigma \widetilde{dW_t} \\
&=rdt+\sigma \big(d\widehat{W_t}+\sigma t\big) \\
&=(r+\sigma^2)dt+\sigma d\widehat{W_t} \tag{43}
\end{align*}
$$

同样地，根据伊藤引理，

$$
\begin{gather*}
ln\frac{S_T}{S_0}～N\bigg(\big(r+\frac{\sigma^2}{2}\big)T, \; \sigma^2T\bigg) \\
S_T=S_0e^{(r+\sigma^2/2)T+\sigma \widehat{W_T}} \tag{44}
\end{gather*}
$$

于是，式(38)的左半部分

$$ \mathcal{Q_S}(S_T\geq K)=\mathcal{Q_S}\bigg(\frac{W_T}{\sqrt{T}} \leq \frac{ln(S_0/K)+(r+\sigma^2/2)T}{\sigma \sqrt{T}}\bigg)=N(d_1) \tag{45} $$

结合式(38)，(40)和(45)，即可得到欧式香草看涨期权在初始时刻的定价

$$ C(0)=S_0N(d_1)-Ke^{-rT}N(d_2) \tag{46} $$

其中，

$$
\begin{gather*}
d_1=\frac{ln(S_0/K)+(r+\sigma^2/2)T}{\sigma \sqrt{T}} \\
d_2=d_1-\sigma \sqrt{T}
\end{gather*}
$$

Q.E.D.

# 后记

以上内容便是现代资产定价理论的核心思想，它们从一个巧妙的角度勾勒出了金融资产的实际市场价格与不同测度下的期望价值之间的联系。在此框架基础上我们可以拓展到对其它以利率、外汇等为标的的衍生品的定价，如考虑多个币种的Quanto特征，针对百慕大Swaption的LGM模型等。

至此我们的资产定价之旅告一段落，本文所介绍的理论也不过是历史上的屠龙之术。在AI机器学习肆虐的今天，肯静下心来研究这些“虚假理论”的人几乎消失殆尽，现在将它们翻出来咀嚼，也只是为了证明这世界上曾经是有“龙”的。

# 参考文献

[1] Hull J. Student solutions manual: *Options, Futures, and other Derivatives* [J]. 2014.

[2] Vecer J. Stochastic Finance: *A Numeraire Approach* [J]. CRC Press, 2011.

[3] Deutsch H P. *Derivatives and Internal Models* [M]. Palgrave Macmillan, 2002.

[4] Kwok, Yue Kuen. *Mathematical models of financial derivatives*, (2008).

[5] Harrison M., Pliska S. *Martingales and stochastic integrals in the theory of continuous trading. Stochastic Processes and their Applications*, 11, (1981), 215–260.

# 附录

**概率空间（Probability space）**

在概率论中，一个概率空间或概率三元组$(\Omega,\mathscr{F},\mathbb{P})$是一个数学构造，它为随机过程提供了一个正式的模型。

一个概率空间有三个组成部分：

- 样本空间$\Omega$，表示所有可能结果的集合；
- 事件空间$\mathscr{F}$，是一个事件的集合，其中每个事件是样本空间中的一个结果集；
- 概率函数$\mathbb{P}$，这个函数为事件空间中的每个事件指定一个概率，该概率是一个介于0和1之间（包括0和1）的数。

**无摩擦市场（Frictionless Markets）**

所谓“无摩擦”，是指：

1. 每种资产都具有流动性（liquid），即在每个时间段，任何买入或卖出指令都可以立即执行；
2. 没有交易成本（transaction costs），即在$t$时刻，每种证券的买入和卖出指令都以相同的价格水平执行；
3. 无论订单大小，执行订单都不会对市场造成影响。

这显然是对现实情况的过度简化，学界已经做了大量工作来放宽这些假设。但从概念的角度来看，它为资产定价理论提供了一个深刻而可行的框架。

**自融资投资组合（Self-financing Portfolio）**

假设一个投资组合由一个权重向量$w(t)=(w_1(t), w_2(t), ..., w_n(t))$定义，则其价值过程表示如下：

$$V(t)=\sum_{1\leq i\leq n}w_i(t)S_i(t)$$

一个投资组合是自融资的，如果满足：

$$dV(t)=\sum_{1\leq i\leq n}w_i(t)dS_i(t)$$

换句话说，自融资投资组合的价值过程不允许注入或撤出资金，它完全由组成金融资产的价格过程及其权重驱动。

**套利机会（Arbitrage Opportunity）**

套利定价理论的一个基本假设是，金融市场不存在套利机会。如果我们能构建一个自融资投资组合，并满足以下条件，就会出现套利机会：

1. 投资组合的初始价值为零，即$V(0)=0$；
2. 投资组合在到期时的价值非负的概率为1，即$P(V(t)\geq 0)=1$；
3. 投资组合到期时的价值为正的概率大于0，即$P(V(T)>0)>0$。

如果一个市场不允许套利机会的存在，我们就说这个市场是无套利的。要求无套利会对价格过程产生重要的影响。

**等价鞅测度（Equivalent Martingale Measure）**

记原始的概率测度为$\mathbb{P}$，等价物$\mathcal{N}(t)$所对应的概率测度为$\mathbb{Q}$，那么概率测度$\mathbb{Q}$被称作$\mathbb{P}$的等价鞅测度，如果满足以下几个性质：

1. 测度$\mathbb{Q}$等价于$\mathbb{P}$，即$\mathbb{Q}$与$\mathbb{P}$有相同的零测集（概率为零对应的事件集）；

2. 相对价格过程$S_i^{\mathcal{N}}(t)$在$\mathbb{Q}$测度下是鞅，即：

$$ S_i^{\mathcal{N}}(s)=\mathbb{E}^{\mathbb{Q}}[S_i^{\mathcal{N}}(t)|\mathscr{F}_s] $$

简单来说，对于一个概率测度，首先它与原始的测度必须是等价的（两个测度对于必然事件和不可能事件的看法是一致的），其次它是一个鞅，那么这个概率测度就可称为原始测度的EMM。

**完备市场（Complete Markets）**

如果每个未定权益（contingent claim）都可以作为自融资交易策略的终值，也就是说，每个合约都可以由市场上存在的金融资产完美复制，那么这个金融市场就称为完备市场，这个过程也被称作**对冲**（hedging）。

换句话说，在一个完备的市场中，存在一个自融资的投资组合$w (t)$，使得$X$等于该投资组合在到期日$T$的价值，即$X=V(T)$。

因此，完备性意味着任何（平方可积的）或有权益都可以通过相关资产的自融资策略来复制。

**Feynman-Kac定理**

考虑一个定义域为$x\in \mathbb{R}$，$t\in[0,T]的$偏微分方程

$$ \frac{\partial{u}}{\partial{t}}(x,t)+\mu(x,t)\frac{\partial{u}}{\partial{x}}(x,t)+\frac{1}{2}\sigma^2(x,t)\frac{\partial^2{u}}{\partial{x^2}}-V(x,t)u(x,t)+f(x,t)=0 $$

满足边界条件

$$ u(x,T)=\psi(x) $$

其中，$\mu,\sigma,\psi,V,f$是已知函数，$T$是一个参数，而$u:\mathbb{R}\times[0,T]\rightarrow\mathbb{R}$是未知函数。Feynman-Kac公式将$u(x,t)$表达为在概率测度$\mathcal{Q}$下的条件期望：

$$ u(x,t)=E^{\mathcal{Q}}\bigg[e^{-\int_t^TV(X_{\tau},\tau)d\tau}\psi(X_T)+\int_t^Te^{-\int_t^{\tau}V(X_{s},s)ds}f(X_{\tau},\tau)d\tau\mid X_t=x\bigg] $$

其中，$X$是一个满足以下条件的伊藤过程：

$$ dX_t=\mu(X_t,t)dt+\sigma(X_t,t)dW_t^{\mathcal{Q}} $$

且$W_t^{\mathcal{Q}}$是一个在$\mathcal{Q}$测度下的维纳过程（也称为布朗运动）。

关于Feynman-Kac公式与风险中性测度之间的联系，点击阅读原文。