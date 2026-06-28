# OneShotPrimalityProofs
For the purpose of this repository, a **one-shot ECPP** is a quadruple of integers $(p,A,x_0,m)$ in which
- $p$ is a positive odd integer,
- $A$ is a nonnegative integer less than $p$ with $A\ne \pm 2\bmod p$,
- $m$ is an integer in $(q+1+2\sqrt{q},p+1+2\sqrt{p}]$, where $q=\lfloor \sqrt{p}\rfloor$, whoese prime divisors are bounded by $n^2$, where $n=\lceil \log_2 p\rceil$,
- $x_0$ is a nonnegative integers less than $p$,

such that there exist integers $B,y_0\in [0,p-1]$ for which $(x_0,y_0)$ is a point of order $m$ on the [Montgomery curve](https://en.wikipedia.org/wiki/Montgomery_curve) $By^2 = x^3 + Ax^2 +X$.

Each [Pomerance triple](https://github.com/AndrewVSutherland/DANGER3/blob/main/README.md) corresponds to a one-shot ECPP in which $m$ is the least power of $2$ in the interval $(q+1+2\sqrt(q),p+1+2\sqrt(p)]$.  It follows that one-shot ECPP's exist for every prime $p>3$.  The key property that one-shot ECPP's share with [Pomerance proofs of primality](https://math.dartmouth.edu/~carlp/PDF/paper62.pdf) is that they can be verified in quasi-quadratic time $O((\log p)^{2+o(1)})$, versus the quasi-cubic time to verify a traditional elliptic curve primality proof (ECPP).

This repository contains the following resources:
- voneshot.py is a Python program that verifies a one-shot ECPP in quasi-quadratic time.
- oneshot8all.txt contains the 799,690 one-shot ECPPs $(p,A,x_0,m)$ with $p\le 2^8$.
- oneshot12prefixes.txt contins the 996,994 prefixes of one-shot ECPPs $(p,A)$ with $p\le 2^{12}$.
- oneshot24.txt contains one-shot ECPPs for each of the 1,077,869 primes $3<p<2^{24}$.
- oneshot.gp is a GP script that uses a brute-force random search to find one-shot ECPPs.

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
<summary>$p=10^{27}+103$,&nbsp; found by <a href="https://math.mit.edu/~drew">Andrew V. Sutherland</a> using the PARI/GP script <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (in this repo) written by Opus 4.8 Max.</summary>
```
1000000000000000000000000103 312974950995669069013171476 172593690963274141822396662 47457808262928
```
</details>
<details>
<summary>$p=10^{28}+331$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
10000000000000000000000000331 5031886505302109097801972542 7590928722467341482534178255 194302826514512
```
</details>
<details>
<summary>$p=10^{29}+319$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
100000000000000000000000000319 31468179295053009742907022163 23123902402618461989178154439 817737156034785
```
</details>
<details>
<summary>$p=10^{30}+57$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
1000000000000000000000000000057 591125717966793476109128213529 197460379572716956878681609455 1173640639212828
```
</details>
<details>
<summary>$p=10^{31}+33$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
10000000000000000000000000000033 4690496079817252168145416687138 8220783064519615672372426718373 5240076766482500
```
</details>
<details>
<summary>$p=10^{32}+49$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
100000000000000000000000000000049 18309249303903019832153244036329 85322474575401452391277964228530 13614910363181120
```
</details>
<details>
<summary>$p=10^{33}+61$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
1000000000000000000000000000000061 648192400153952751799649675566254 429346140800532487176183128471515 60036892806592588
```
</details>
<details>
<summary>$p=10^{34}+193$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
10000000000000000000000000000000193 2594753449944574831102996807476719 6733173628454929111267082029383756 169943089227918080
```
</details>
<details>
<summary>$p=10^{35}+69$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
100000000000000000000000000000000069 93977100671481669191332747972651177 52101934975675178822779890741815362 382471270587522580
```
</details>
<details>
<summary>$p=10^{36}+67$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
1000000000000000000000000000000000067 353080590237600292016249222126744754 473830482386688141513982236889280987 1182690518354585184
```
</details>
<details>
<summary>$p=10^{37}+43$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
10000000000000000000000000000000000043 2717297970637349065380416672384095184 4511737206111955351917332049377553718 3739337326854726564
```
</details>
<details>
<summary>$p=10^{38}+133$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a>.</summary>
```
100000000000000000000000000000000000133 70845294891976403444554278469676530455 87917117948218547290408848541807294166 12239686139389993376
```
</details>
<details>
<summary>$p=10^{39}+3$,&nbsp; via <a href="https://github.com/AndrewVSutherland/OneShotPrimalityProofs/blob/main/oneshot.gp">oneshot.gp</a> (about 4 CPU minutes).</summary>
```
1000000000000000000000000000000000000003 122886961756874115892864204812888757733 840437353385309934285823630402884859950 35709281381466792384
```
</details>
<details>
<summary>$p=10^{40}+121$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 - Extra High with <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/main/parallel_search_oneshot.py">parallel_search_oneshot.py</a> in this repo (8 workers; about 15 wall seconds for the successful parallel run, after an earlier ~10 CPU-minute single-worker attempt).</summary>
```
10000000000000000000000000000000000000121 159417335712131629150530624126527065617 6380001157648721637516633150027366007494 105540040423836213192
```
</details>
<details>
<summary>$p=10^{41}+109$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 - Extra High with <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/main/parallel_search_oneshot.py">parallel_search_oneshot.py</a> in this repo (8 workers; about 5 wall minutes / 40 CPU minutes).</summary>
```
100000000000000000000000000000000000000109 39435640101422654764599095494847602099232 36831500717974458616819433974636974324447 363491440182266265472
```
</details>
<details>
<summary>$p=10^{42}+63$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 - Extra High with <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/main/parallel_search_oneshot.py">parallel_search_oneshot.py</a> in this repo (10 workers; about 85 wall seconds / 14 CPU minutes).</summary>
```
1000000000000000000000000000000000000000063 343943387892846314235425590464547215426859 280823505882550748075957411703530911632701 1131366670427546681976
```
</details>
<details>
<summary>$p=10^{43}+57$,&nbsp; found by <a href="https://alexamclain.com/">Alexa McLain</a> using GPT 5.5 - Extra High with <a href="https://github.com/alexamclain/OneShotPrimalityProofs/blob/main/parallel_search_oneshot.py">parallel_search_oneshot.py</a> in this repo (10 workers; about 8 wall minutes / 80 CPU minutes).</summary>
```
10000000000000000000000000000000000000000057 4489380030712735248598126581411880758875345 9165735316113841775721569461780378543380092 9853418716696366234445
```
</details>

Contributors (both human and AI) are welcome to submit pull requests to this repo, provided they follow the guidelines below:
- new entries should be the least prime greater than a power of 10 larger than any currently listed;
- include the name of a human and a link to their web page (if available);
- specify the model (and effort level) of any LLM used;
- give a rough estimate of the computationl resources used (e.g. CPU/GPU minutes/hours);
- provide a link to a GitHub repo with code that can be used to reproduce the example.
