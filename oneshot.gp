/* oneshot.gp -- compute a one-shot ECPP certificate for a probable prime p > 3.
 * Written by Opus 4.8 Max.
 *
 * Searches random curves  E_A : y^2 = x^3 + A*x^2 + x  over F_p, and their
 * quadratic twists, for a group order with an n^2-smooth factor exceeding
 * (p^{1/4}+1)^2  (n = bit length of p), then finds a point of large smooth order.
 *
 * The point order is obtained by stripping primes from the SMOOTH part s only; the
 * n^2-rough cofactor r = #E / s is never factored (it may be genuinely hard to factor).
 *
 * The certificate (p, A, x0, m) means: on E_A the point with x-coordinate x0 has order m,
 * with m > (p^{1/4}+1)^2 and m n^2-smooth -- a Pomerance/Goldwasser-Kilian ECPP certificate.
 *
 * Usage:
 *     echo 'printcert(<p>)' | gp -q smoothcert.gp
 */

SC_curves = 0;

/* n^2-smooth part s of N with the rough cofactor r = N/s, by trial division over primes <= B */
smoothpart(N, B) = {
  my(s = 1, r = N);
  forprime(q = 2, B, while(r % q == 0, r /= q; s *= q));
  [s, r];
};

/* Montgomery x-only arithmetic for E_A and its quadratic twist. */
sc_xdbl(X, Z, A, p) = {
  my(XX = (X * X) % p, ZZ = (Z * Z) % p, XZ = (X * Z) % p, X2, Z2);
  X2 = ((XX - ZZ) * (XX - ZZ)) % p;
  Z2 = (4 * XZ) % p * ((XX + A * XZ + ZZ) % p) % p;
  [X2, Z2];
};

sc_xadd(X1, Z1, X2, Z2, Xd, Zd, p) = {
  my(a = (X1 - Z1) * (X2 + Z2) % p, b = (X1 + Z1) * (X2 - Z2) % p, s, d);
  s = (a + b) % p;
  d = (a - b) % p;
  [Zd * (s * s % p) % p, Xd * (d * d % p) % p];
};

sc_ladder(k, XP, ZP, A, p) = {
  if(k == 0, return([1, 0]));
  XP %= p; ZP %= p;
  if(k == 1, return([XP, ZP]));
  my(Xd = XP, Zd = ZP, X0 = XP, Z0 = ZP, R = sc_xdbl(XP, ZP, A, p), X1 = R[1], Z1 = R[2], bits = binary(k), T);
  for(i = 2, #bits,
    if(bits[i] == 0,
      T = sc_xadd(X0, Z0, X1, Z1, Xd, Zd, p); X1 = T[1]; Z1 = T[2];
      T = sc_xdbl(X0, Z0, A, p); X0 = T[1]; Z0 = T[2],
      T = sc_xadd(X0, Z0, X1, Z1, Xd, Zd, p); X0 = T[1]; Z0 = T[2];
      T = sc_xdbl(X1, Z1, A, p); X1 = T[1]; Z1 = T[2]
    )
  );
  [X0, Z0];
};

sc_xisinf(P, p) = ((P[2] % p) == 0 && gcd(P[1] % p, p) == 1);
sc_affine_x(P, p) = lift(Mod(P[1], p) / Mod(P[2], p));

sc_curve_side(A, x, p) = kronecker((x * ((x * x + A * x + 1) % p)) % p, p);

sc_random_x_on_side(A, p, side) = {
  my(x);
  for(t = 1, 256,
    x = random(p);
    if(sc_curve_side(A, x, p) == side, return(x))
  );
  -1;
};

/* Try a known group order N for E_A (side=1) or its quadratic twist (side=-1). */
sc_try_order(A, p, N, B, bound, side) = {
  my(sr = smoothpart(N, B), s = sr[1], r = sr[2], fs, x, Q, T, ord, q, d, fo, Qm);
  if(s <= bound, return(0));                              \\ smooth factor too small
  fs = factor(s)[, 1];
  for(t = 1, 64,
    x = sc_random_x_on_side(A, p, side);
    if(x < 0, next);
    Q = sc_ladder(r, x, 1, A, p);                         \\ order(Q) divides s
    if((Q[2] % p) == 0, next);                            \\ Q = O, resample x
    ord = s;
    for(i = 1, #fs,
      q = fs[i];
      while(ord % q == 0,
        T = sc_ladder(ord / q, Q[1], Q[2], A, p);
        if(sc_xisinf(T, p), ord /= q, break)
      )
    );
    if(ord > bound,
      d = ord; fo = factor(ord)[, 1];                     \\ reduce point to minimal smooth order > bound
      forstep(jj = #fo, 1, -1, q = fo[jj]; while(d % q == 0 && d / q > bound, d = d / q));
      Qm = sc_ladder(ord / d, Q[1], Q[2], A, p);          \\ ord(Qm) = d, still > bound, still smooth
      if((Qm[2] % p) == 0, next);
      return([A, sc_affine_x(Qm, p), d]))
  );
  0;
};

/* Try one random curve E_A over F_p.  Return [A, x0, m] if it yields a point of n^2-smooth
 * order m > bound, else 0.  B = n^2. */
sc_try(p, B, bound) = {
  my(A = random(p), E = ellinit([0, A, 0, 1, 0], p));
  if(#E == 0, return(0));                                 \\ singular (A == +-2 mod p)
  my(N = ellcard(E), res);
  res = sc_try_order(A, p, N, B, bound, 1);
  if(type(res) == "t_VEC", return(res));
  res = sc_try_order(A, p, 2 * p + 2 - N, B, bound, -1);
  if(type(res) == "t_VEC", return(res));
  0;
};
export(smoothpart);
export(sc_try);

scbound(p) = sqrtint(p) + 1 + sqrtint(4 * sqrtint(p));   \\ integer form of (p^{1/4}+1)^2

scsetup(p) = {                                           \\ shared argument checks
  if(!ispseudoprime(p), error("smoothcert: p is composite"));
  if(p <= 3, error("smoothcert: need p > 3"));
};

smoothcert(p) = {
  scsetup(p);
  my(B = #binary(p)^2, bound = scbound(p), res);
  SC_curves = 0;
  while(1,
    SC_curves++;
    res = sc_try(p, B, bound);
    if(type(res) == "t_VEC", return([p, res[1], res[2], res[3]]))
  );
};

printcert(p) = { my(c = smoothcert(p)); print(c[1], " ", c[2], " ", c[3], " ", c[4]); };
