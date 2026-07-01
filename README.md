# OneShotPrimalityProofs
For the purpose of this repository, a **one-shot ECPP** is a tuple of integers $(p,A,x_0,m,q_1,\ldots,q_k)$ in which
- $p$ is a positive odd integer,
- $A$ is a nonnegative integer less than $p$ with $A\ne \pm 2\bmod p$,
- $x_0$ is a nonnegative integer less than $p$,
- $m$ is an $n^4$-smooth integer, where $n=\lceil \log_2 p\rceil$, satisfying $L < m < L\cdot r$, where $L=q+1+\lfloor 2\sqrt{q}\rfloor$ with $q=\lfloor\sqrt{p}\rfloor$ and $r$ is the least prime divisor of $m$,
- $q_1<\cdots<q_k$ are the prime divisors of $m$ in the interval $(n^2,n^4)$,

such that there exist integers $B,y_0\in [0,p-1]$ for which $(x_0,y_0)$ is a point of order $m$ on the [Montgomery curve](https://en.wikipedia.org/wiki/Montgomery_curve) $By^2 = x^3 + Ax^2 +x$.

Each [Pomerance triple](https://github.com/AndrewVSutherland/DANGER3/blob/main/README.md) corresponds to a one-shot ECPP with $k=0$ in which $m$ is the least power of $2$ exceeding $q+1+2\sqrt{q}$, where $q=\lfloor\sqrt{p}\rfloor$.  It follows that one-shot ECPPs exist for every prime $p>3$.  The key property that one-shot ECPPs share with [Pomerance proofs of primality](https://math.dartmouth.edu/~carlp/PDF/paper62.pdf) is that they can be verified in quasi-quadratic time $O((\log p)^{2+o(1)})$, versus the quasi-cubic time to verify a traditional elliptic curve primality proof (ECPP).

This repository contains the following resources:
- voneshot.py is a Python program that verifies a one-shot ECPP in quasi-quadratic time.
- oneshot8all.txt contains the 202,260 one-shot ECPPs $(p,A,x_0,m,q_1,\ldots,q_k)$ with $p\le 2^8$.
- oneshot12prefixes.txt lists the 1,068,923 unique prefixes $(p,A)$ among all one-shot ECPPs with $p\le 2^{12}$
- oneshot.gp is a GP script that uses a brute-force random search to find one-shot ECPPs.

This project is part of the DARPA expMath program.

**Challenge**
Below is a list of one-shot ECPPs for the least prime $p > 10^n$ for increasing values of $n$.  Can you extend this list?

<details>
<summary>$p=10^{20}+39$,&nbsp; Pomerance proof by <a href="https://www.wits.ac.za/people/academic-a-z-listing/j/vjejjalawitsacza/">Vishnu Jejjala</a> using GPT 5.4 Pro.</summary>
```
100000000000000000039 80635707401894747894 31614069099331127513 17179869184
```
</details>
<details>
<summary>$p=10^{21}+117$,&nbsp Pomerance proof by <a href="https://cos.northeastern.edu/people/fabian-ruehle/">Fabian Ruehle</a> using Claude Code Opus 4.6.</summary>
```
1000000000000000000117 51546435219887079991 144666470127730980460 34359738368
```
</details>
<details>
<summary>$p=10^{22}+9$,&nbsp Pomerance proof found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 Codex.</summary>
```
10000000000000000000009 9992566338662824267458 3694769590833803032125 137438953472
```
</details>
<details>
<summary>$p=10^{23}+117$,&nbsp Pomerance proof found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 Codex.</summary>
```
100000000000000000000117 24163028207499560363686 64911014007772963770218 549755813888
```
</details>
<details>
<summary>$p=10^{24}+7$,&nbsp; Pomerance proof found by <a href="https://janeshi99.github.io/">Jane Shi</a> using Claude Fable 5.</summary>
```
1000000000000000000000007 38923582678463553756710 843367907077058108520461 1099511627776
```
</details>
<details>
<summary>$p=10^{25}+13$,&nbsp Pomerance proof found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 Codex.</summary>
```
10000000000000000000000013 5863342488035851054212447 9636258147581954669181726 4398046511104
```
</details>
<details>
<summary>$p=10^{26}+67$,&nbsp Pomerance proof found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 Codex.</summary>
```
100000000000000000000000067 78462973492772865017160395 27732450411057582323409556 17592186044416
```
</details>
<details>
<summary>$p=10^{27}+103$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~2 CPU seconds).</summary>
```
1000000000000000000000000103 632259414096052310182774760 241933189256530284790900257 51496302105884 1310041
```
</details>
<details>
<summary>$p=10^{28}+331$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~2 CPU seconds).</summary>
```
10000000000000000000000000331 3819358685794209339778268422 305961141031129319858787556 102836022984716 26237 858787
```
</details>
<details>
<summary>$p=10^{29}+319$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~4 CPU seconds).</summary>
```
100000000000000000000000000319 47963730417932095477544369183 33344234680510331383928482742 631463703703722 86981 1606859
```
</details>
<details>
<summary>$p=10^{30}+57$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~3 CPU seconds).</summary>
```
1000000000000000000000000000057 687867969791064835508699233167 938392059726327280925731259947 2018066682255505 523427 15736687
```
</details>
<details>
<summary>$p=10^{31}+33$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~3 CPU seconds).</summary>
```
10000000000000000000000000000033 1569321684903152408827641113136 5654198663631043026701645643834 3313183492084040 158551 4882393
```
</details>
<details>
<summary>$p=10^{32}+49$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~1 CPU second).</summary>
```
100000000000000000000000000000049 66474910464743596764054967879224 38828122544783994860995928050644 10293985643530744 9420863
```
</details>
<details>
<summary>$p=10^{33}+61$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~9 CPU seconds).</summary>
```
1000000000000000000000000000000061 353026367407525499860232502709688 929870072773368076702362066680356 47514019175283624 17053 64613 1796759
```
</details>
<details>
<summary>$p=10^{34}+193$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~17 CPU seconds).</summary>
```
10000000000000000000000000000000193 8739862166980634595241412376168643 3520620427933902296076932580876513 301416586545004223 44623 1067789 6325909
```
</details>
<details>
<summary>$p=10^{35}+69$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~26 CPU seconds).</summary>
```
100000000000000000000000000000000069 43571634169656825484488799600262955 73324636112609490847888802702893858 14888340044140359809 734737 4341461 4667437
```
</details>
<details>
<summary>$p=10^{36}+67$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~21 CPU seconds).</summary>
```
1000000000000000000000000000000000067 546957193871014044620465668376155626 266789102886001254668936137853016622 1769979554256308244 1344943 13467863
```
</details>
<details>
<summary>$p=10^{37}+43$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~30 CPU seconds).</summary>
```
10000000000000000000000000000000000043 5237715629079103587149260467700428325 9472337478832328873104881584937490583 6186260659965100462 41863 12859657
```
</details>
<details>
<summary>$p=10^{38}+133$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~11 CPU seconds).</summary>
```
100000000000000000000000000000000000133 47587324196748505663342988875144682210 54979457230785623959485653018410163282 16591244954303207712 380197 687233
```
</details>
<details>
<summary>$p=10^{39}+3$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~16 CPU seconds).</summary>
```
1000000000000000000000000000000000000003 504583214550958244930738920650393491192 783954448462368567077571697557803213454 47479781621775216076 1892911 34868611
```
</details>
<details>
<summary>$p=10^{40}+121$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~11 CPU seconds).</summary>
```
10000000000000000000000000000000000000121 2555590210029791760837835235116824050712 7803267868978634318147510268900254553126 140275114734315966012 5729183 300008747
```
</details>
<details>
<summary>$p=10^{41}+109$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~65 CPU seconds).</summary>
```
100000000000000000000000000000000000000109 87097305941929273427731132809962651081285 30823582247829528910553207214014982417129 544013220940041406102 31097609 47675417
```
</details>
<details>
<summary>$p=10^{42}+63$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~23 CPU seconds).</summary>
```
1000000000000000000000000000000000000000063 529506758815175640384490072508073810688326 930852371004292840865610811517730303303233 1220387101381184380733 26959 12462617
```
</details>
<details>
<summary>$p=10^{43}+57$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~40 CPU seconds).</summary>
```
10000000000000000000000000000000000000000057 2297567934978871941940436975827326448175793 5333694566450187539051303802957267613703452 3201092422777268935128 2382481 6766237
```
</details>
<details>
<summary>$p=10^{44}+31$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~17 CPU seconds).</summary>
```
100000000000000000000000000000000000000000031 83605012090025919814047942002681416414003837 20983291775532904412388654109140995110084027 10026627377625427845274 24223 24371 57075901
```
</details>
<details>
<summary>$p=10^{45}+9$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~169 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000009 445135896715836861872058430558119402113657317 580092437731663015231074250204120036653708361 35083798402964252071240 234187 536561 7129877
```
</details>
<details>
<summary>$p=10^{46}+121$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~74 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000121 8151755648368274577008537475923202273172438992 5510692970318980714549217757764134621563504704 128800712446011313424307 27967 166541 3506023
```
</details>
<summary>$p=10^{47}+33$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~107 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000033 55112216345782201038699272011159355107796454764 95436945926088979849959572902251388077592257351 324092508714303587772108 563117 8053139 17363201
```
</details>
<details>
<summary>$p=10^{48}+193$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~48 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000193 707741292887771625707020666296880442101300419986 651661800356255754291649471544519774459713356937 1291577020489510362813952 63311 14471257
```
</details>
<details>
<summary>$p=10^{49}+9$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~48 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000009 7508802625092824753815795510429506581066157556192 7804725873907977597314105710897628490360424602840 4090193719245769518347680 777641 2107771 103286693
```
</details>
<details>
<summary>$p=10^{50}+151$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (~27 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000151 6437009016641369174910085274409395465870501856011 10538254878888005413405709303009388193264578918912 10329133743438851861485056 325151243
```
</details>
<details>
<summary>$p=10^{51}+121$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> with PARI seed 2031070117, using GPT-5 Codex (~33 CPU seconds to reproduce the winning seed).</summary>
```
1000000000000000000000000000000000000000000000000121 929729204722440022586893717956999583201547721462854 852931546149610240034551633260547527121659598818032 48961580129575478246279636 792317 214803473
```
</details>

Contributors (both human and AI) are welcome to submit pull requests to this repo, provided they follow the guidelines below:
- new entries should be the least prime greater than a power of 10 larger than any currently listed;
- include the name of a human and a link to their web page (if available);
- specify the model (and effort level) of any LLM used;
- give a rough estimate of the computational resources used (e.g. CPU/GPU minutes/hours);
- provide a link to a GitHub repo with code that can be used to reproduce the example.
