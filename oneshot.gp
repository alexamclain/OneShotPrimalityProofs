/* oneshot.gp -- compute a one-shot n^4-smooth ECPP certificate for a probable prime p > 3.
 * Written by Opus 4.8 Max.  (Modified for the n^4-smooth certificate format.)
 *
 * Searches random curves  E_A : y^2 = x^3 + A*x^2 + x  over F_p for one whose order has
 * an n^4-smooth factor exceeding (p^{1/4}+1)^2  (n = bit length of p), then finds a point
 * of minimal large smooth order on it.
 *
 * The point order is obtained by stripping primes from the SMOOTH part s only; the
 * n^4-rough cofactor r = #E / s is never factored (it may be genuinely hard to factor).
 *
 * The certificate (p, A, x0, m, q1, ..., qk) means: on E_A the point with x-coordinate x0
 * has order m, where  bound < m < L*r  with bound = L = (p^{1/4}+1)^2 and r the least prime
 * of m, m is n^4-smooth, and q1 < ... < qk are the prime divisors of m lying in (n^2, n^4).
 * Carrying the q_i lets a verifier trial-divide only to n^2 while still factoring m fully --
 * a Pomerance/Goldwasser-Kilian ECPP certificate.  (Allowing primes up to n^4 rather than
 * n^2 makes a qualifying smooth factor far more common, so far fewer curves are tried.)
 *
 * Usage:
 *     echo 'printcert(<p>)' | gp -q oneshot.gp
 */

SC_curves = 0;

/* n^4-smooth part s of N with the rough cofactor r = N/s, by trial division over primes <= B */
smoothpart(N, B) = {
  my(s = 1, r = N);
  forprime(q = 2, B, while(r % q == 0, r /= q; s *= q));
  [s, r];
};

/* Try one random curve E_A over F_p.  Return [A, x0, m, qs] if it yields a point of
 * n^4-smooth order m with bound < m < L*r (L = bound, r the least prime of m), where qs is
 * the (ascending) vector of prime divisors of m in (n^2, n^4); else 0.  B = n^4, n2 = n^2. */
sc_try(p, B, n2, bound) = {
  my(A = random(p), E = ellinit([0, A, 0, 1, 0], p));
  if(#E == 0, return(0));                                 \\ singular (A == +-2 mod p)
  my(N = ellcard(E), sr = smoothpart(N, B), s = sr[1], r = sr[2]);
  if(s <= bound, return(0));                              \\ smooth factor too small
  my(fs = factor(s)[, 1], P, Q, ord, q, d, fo, fd, lp, qs, Qm);  \\ fs = distinct primes of s
  for(t = 1, 64,
    P = random(E); Q = ellmul(E, P, r);                   \\ order(Q) divides s
    if(#Q == 1, next);                                    \\ Q = O, resample P
    ord = s;
    for(i = 1, #fs, q = fs[i]; while(ord % q == 0 && #ellmul(E, Q, ord/q) == 1, ord /= q));
    if(ord > bound,
      d = ord; fo = factor(ord)[, 1];                     \\ reduce point to minimal smooth order > bound
      forstep(jj = #fo, 1, -1, q = fo[jj]; while(d % q == 0 && d/q > bound, d = d/q));
      fd = factor(d)[, 1]; lp = fd[1];                    \\ fd ascending; lp = least prime of reduced d
      if(d >= bound * lp, next);                          \\ enforce strict m < L*r (rare boundary); resample
      qs = select(qq -> qq > n2, fd);                     \\ q_i: primes of m in (n^2, n^4) (all < n^4 since m is n^4-smooth)
      Qm = ellmul(E, Q, ord/d);                           \\ ord(Qm) = d, still > bound, still smooth
      return([A, lift(Qm[1]), d, qs]))
  );
  0;
};
export(smoothpart);
export(sc_try);

scbound(p) = sqrtint(p) + 1 + sqrtint(4 * sqrtint(p));   \\ integer form of (p^{1/4}+1)^2

scsetup(p) = {                                           \\ shared argument checks
  if(!ispseudoprime(p), error("oneshot: p is composite"));
  if(p <= 3, error("oneshot: need p > 3"));
};

smoothcert(p) = {
  scsetup(p);
  my(n = #binary(p), B = n^4, n2 = n^2, bound = scbound(p), res);
  SC_curves = 0;
  while(1,
    SC_curves++;
    res = sc_try(p, B, n2, bound);
    if(type(res) == "t_VEC", return([p, res[1], res[2], res[3], res[4]]))
  );
};

printcert(p) = {                                         \\ "p A x0 m q1 ... qk"
  my(c = smoothcert(p));
  printf("%d %d %d %d", c[1], c[2], c[3], c[4]);
  for(i = 1, #c[5], printf(" %d", c[5][i]));
  print();
};
