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
<details>
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
<details>
<summary>$p=10^{52}+327$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 20312701, using GPT-5 Codex high effort (~27 CPU seconds to find in calibration).</summary>
```
10000000000000000000000000000000000000000000000000327 7819922362141738790860795752243355235058320892089316 7677168746676345585034829879318762811857306212562145 403821991422963980467893787 965953 1628279 8738053
```
</details>
<details>
<summary>$p=10^{53}+171$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026080345, using GPT-5 Codex high effort (~13 CPU minutes in the sweep; winning seed reproduces in ~11 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000171 5209047513295235928207653344096176850712215554033339 26735609868408159509019275983731797922094955767574809 368129996986311511658484088 1015409 16274579 773710699
```
</details>
<details>
<summary>$p=10^{54}+31$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026078427, using GPT-5 Codex high effort (~17 CPU minutes in the sweep; winning seed reproduces in ~56 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000031 344269491748775889097174968676778767687570533536808621 320634034569072401151840573556224629271347673429408057 1870155969699690579138787636 27742931 78229807
```
</details>
<details>
<summary>$p=10^{55}+21$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026083572, using GPT-5 Codex high effort (~19 CPU minutes in the sweep; winning seed reproduces in ~47 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000021 171926072097157976860182282325257011548183139472740755 2987699775192806589572591406777102628802697215074047698 6230254348515818315463167384 130191349 389098051
```
</details>
<details>
<summary>$p=10^{56}+3$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026084681, using GPT-5 Codex high effort (~13 CPU minutes in the sweep; winning seed reproduces in ~13 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000003 95552651697522473218970294613104323198831778271577913011 71924812754849414035373164820431902742815561608238648101 15869781255784280687605003324 523829 130103929 455366251
```
</details>
<details>
<summary>$p=10^{57}+279$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026081754, using GPT-5 Codex high effort (~19 CPU minutes in the sweep; winning seed reproduces in ~25 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000279 430824429250832526992365190903862047421205801317081746246 233116881189951296502831037492997547567962330460372595349 50043216584833342784906043144 98377 29233747 195423689
```
</details>
<details>
<summary>$p=10^{58}+159$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026082863, using GPT-5 Codex high effort (~23 CPU minutes in the sweep; winning seed reproduces in ~46 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000159 2281727843455138080267114137001835199896502300627223163552 508884327622375061523205498883859852798826790544257417171 111933175837800343548547824748 847681 1368401 181134341
```
</details>
<details>
<summary>$p=10^{59}+19$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026083972, using GPT-5 Codex high effort (~37 CPU minutes in the sweep; winning seed reproduces in ~98 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000000019 10051879614222555164401871746484919502901346940706414402939 93567331462763384667129620109456599796024293170358892128860 504610162012325876128702078008 3708791 54523519 81378971
```
</details>
<details>
<summary>$p=10^{60}+7$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026079027, using GPT-5 Codex high effort (~25 CPU minutes in the widened sweep; winning seed reproduces in ~41 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000000007 471906142857897370628256623352865597231582219698155951859352 123536947612166753741815825478855499721942159274413535899324 1223917746835797194801250618176 52081 125387 301319 222464999
```
</details>
<details>
<summary>$p=10^{61}+93$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026077109, using GPT-5 Codex high effort (~54 CPU minutes in the sweep; winning seed reproduces in ~105 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000000093 634651994351104364789371485564111627088558257645066009707430 5295322451280994658981320376041568911125675798315148080777024 4370602356607389131784863285568 3558803 420520361 521575151
```
</details>
<details>
<summary>$p=10^{62}+447$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026082254, using GPT-5 Codex high effort (~84 CPU minutes in the sweep; winning seed reproduces in ~189 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000000000447 96544254141122109073613800261988577334080183302005240606199841 85718385972652023008377452347946383013438501693153244829229256 14394311320355609559048132074428 5904517 108426229 137089019
```
</details>
<details>
<summary>$p=10^{63}+121$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026077309, using GPT-5 Codex high effort (~8 CPU minutes before stop-after-hit; winning seed reproduces in ~49 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000000000121 595729012769220261516077680623709934569489128986723006340619953 673282922523184225067052047303566010690202675216955146200115210 123983000445034822065036807875405 2785847 14134073 29718467 32650997
```
</details>
<details>
<summary>$p=10^{64}+57$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026076400, using GPT-5 Codex high effort (~28 CPU minutes before stop-after-hit; winning seed reproduces in ~173 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000000000057 1996157043492434263006767315784072460057070528401835657765212229 530037400874910613306613053890934228019791685133614982508127399 138755386799642525706225654818220 1599583 424217341 1953965239
```
</details>
<details>
<summary>$p=10^{65}+49$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026077509, using GPT-5 Codex high effort (~22 CPU minutes before stop-after-hit; winning seed reproduces in ~135 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000000000000049 9489723132733149497630252881012531443147208400259899358595925299 47272530465839009968378449249293697423249548398288546321546880854 408373727233277939592814815365328 653143 1954289 1172551019
```
</details>
<details>
<summary>$p=10^{66}+49$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026080636, using GPT-5 Codex high effort (~25 CPU minutes before stop-after-hit; winning seed reproduces in ~157 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000000000000049 680941551180738306125843656000543535525561927857672527926143597776 643122038029398752081933484892286163665734454402588989894011650113 1361312758406518840030015659305928 547559 1138999 2681027 1499216123
```
</details>
<details>
<summary>$p=10^{67}+49$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026080736, using GPT-5 Codex high effort (~2 CPU minutes before stop-after-hit; winning seed reproduces in ~16 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000000000000049 4300022087799932868173561545921543753509027735535944641168673373861 3498800944789861096651737687703571588845425772478602734894168905803 19540638454921707373179153758408233 511109 17377237 153340513 2066523839
```
</details>
<details>
<summary>$p=10^{68}+99$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026084872, using GPT-5 Codex high effort (~47 CPU minutes before stop-after-hit; winning seed reproduces in ~286 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000000000000000099 39791207360803030067799615401766363867600449181672689587476534922232 79371805174379626951445798684414862480055687898561331602097268472606 15595791389229634400890159716697548 463231 12576037 543742819 1791660557
```
</details>
<details>
<summary>$p=10^{69}+9$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026079927, using GPT-5 Codex high effort (~31 CPU minutes before stop-after-hit; winning seed reproduces in ~192 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000000000000000009 138909447683767362938353532474360452460922491939445271305658245217848 983899115951346329611088518402116335946334272008873683092389348407248 128908639575213066810163495594483019 127583 5244901 12467047 140058929
```
</details>
<details>
<summary>$p=10^{70}+33$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026082045, using GPT-5 Codex high effort (~25 CPU seconds before stop-after-hit; winning seed reproduces in ~15 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000000000000000033 9281987330009515995762734943090576817575989500715340595578695631661571 3297674305228793633332623643894648248925398365999270217825972488989866 165382690116838958209269686585701402 271849 1219111 37803287
```
</details>
<details>
<summary>$p=10^{71}+273$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026079118, using GPT-5 Codex high effort (~22 CPU minutes before stop-after-hit; winning seed reproduces in ~140 CPU seconds).</summary>
```
100000000000000000000000000000000000000000000000000000000000000000000273 61510327714574494210139260555654778114006269431989830084449374114717666 19597437607774374737451003479022024400887943975071206209477864615642021 373159589853552116465127067205765295 66070769 272346961 553472749
```
</details>
<details>
<summary>$p=10^{72}+39$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026080227, using GPT-5 Codex high effort (~196 CPU minutes before stop-after-hit; winning seed reproduces in ~1186 CPU seconds).</summary>
```
1000000000000000000000000000000000000000000000000000000000000000000000039 298369531518639777035037322093522711946691660987814616604488929357201459 195733311453103323639889101128092044986438149388952116150344757838730836 8286613817274529235396718961147869571 17460217 100842383 2719971521 2822666257
```
</details>
<details>
<summary>$p=10^{73}+79$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> via <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/codex/ledger-search-lab/search_lab.py">search_lab.py</a> <code>two_sided_factor</code> with PARI seed 2026083354, using GPT-5 Codex high effort (~78 CPU minutes before stop-after-hit; winning seed reproduces in ~475 CPU seconds).</summary>
```
10000000000000000000000000000000000000000000000000000000000000000000000079 3629571014457520202712302992507525034865648247956933724727984763632832421 3724935890053439045817924532475961397094469485480247112607697058532774506 4025951649000038409419256886717068968 147919 19305821 29663401 143551789
```
</details>

Contributors (both human and AI) are welcome to submit pull requests to this repo, provided they follow the guidelines below:
- new entries should be the least prime greater than a power of 10 larger than any currently listed;
- include the name of a human and a link to their web page (if available);
- specify the model (and effort level) of any LLM used;
- give a rough estimate of the computational resources used (e.g. CPU/GPU minutes/hours);
- provide a link to a GitHub repo with code that can be used to reproduce the example.
