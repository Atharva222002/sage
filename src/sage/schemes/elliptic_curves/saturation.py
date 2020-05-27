# -*- coding: utf-8 -*-
r"""
Saturation of Mordell-Weil groups of elliptic curves over number fields

Points `P_1`, `\dots`, `P_r` in `E(K)`, where `E` is an elliptic curve
over a number field `K`, are said to be `p`-saturated if no linear
combination `\sum n_iP_i` is divisible by `p` in `E(K)` except
trivially when all `n_i` are multiples of `p`.  The points are said to
be saturated if they are `p`-saturated at all primes; this is always
true for all but finitely many primes since `E(K)` is a
finitely-generated Abelian group.

The process of `p`-saturating a given set of points is implemented
here.  The naive algorithm simply checks all `(p^r-1)/(p-1)`
projective combinations of the points, testing each to see if it can
be divided by `p`.  If this occurs then we replace one of the points
and continue.  The function :meth:`p_saturation` does one step of
this, while :meth:`full_p_saturation` repeats until the points are
`p`-saturated.  A more sophisticated algorithm for `p`-saturation is
implemented which is much more efficient for large `p` and `r`, and
involves computing the reduction of the points modulo auxiliary primes
to obtain linear conditions modulo `p` which must be satisfied by the
coefficients `a_i` of any nontrivial relation.  When the points are
already `p`-saturated this sieving technique can prove their
saturation quickly.

The method :meth:`saturation` of the class EllipticCurve_number_field
applies full `p`-saturation at any given set of primes, or can compute
a bound on the primes `p` at which the given points may not be
`p`-saturated.  This involves computing a lower bound for the
canonical height of points of infinite order, together with estimates
from the geometry of numbers.

AUTHORS:

- Robert Bradshaw

- John Cremona

"""
#*****************************************************************************
#       Copyright (C) 2017 Robert Bradshaw <robertwb@math.washington.edu>
#                          John Cremona <john.cremona@gmail.com>
#                          William Stein <wstein@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

from sage.rings.finite_rings.all import GF
from sage.rings.all import ZZ

def p_projections(G, Plist, p, debug=False):
    r"""

    INPUT:

    - `G` - the Abelian group of an elliptic curve over a finite field.

    - `Plist` - a list of points on that curve.

    - `p` - a prime number.

    OUTPUT:

    A list of $r\le2$ vectors in $\F_p^n$, the images of the points in
    $G \otimes \F_p$, where $r$ is the number of vectors is the
    $p$-rank of `G`.

    ALGORITHM:

    First project onto the $p$-primary part of `G`.  If that has
    $p$-rank 1 (i.e. is cyclic), use discrete logs there to define a
    map to $\F_p$, otherwise use the Weil pairing to define two
    independent maps to $\F_p$.

    EXAMPLES:

    This curve has three independent rational points::

        sage: E = EllipticCurve([0,0,1,-7,6])

    We reduce modulo $409$ where its order is $3^2\cdot7^2$; the
    $3$-primary part is non-cyclic while the $7$-primary part is
    cyclic of order $49$::

        sage: F = GF(409)
        sage: EF = E.change_ring(F)
        sage: G = EF.abelian_group()
        sage: G
        Additive abelian group isomorphic to Z/147 + Z/3 embedded in Abelian group of points on Elliptic Curve defined by y^2 + y = x^3 + 402*x + 6 over Finite Field of size 409
        sage: G.order().factor()
        3^2 * 7^2

    We construct three points and project them to the $p$-primary
    parts for $p=2,3,5,7$, yielding 0,2,0,1 vectors of length 3 modulo
    $p$ respectively.  The exact vectors output depend on the computed
    generators of `G`::

        sage: Plist = [EF([-2,3]), EF([0,2]), EF([1,0])]
        sage: from sage.schemes.elliptic_curves.saturation import p_projections
        sage: [(p,p_projections(G,Plist,p)) for p in primes(11)]  # random
        [(2, []), (3, [(0, 2, 2), (2, 2, 1)]), (5, []), (7, [(5, 1, 1)])]
        sage: [(p,len(p_projections(G,Plist,p))) for p in primes(11)]
        [(2, 0), (3, 2), (5, 0), (7, 1)]

    """
    if debug:
        print("In p_projections(G,Plist,p) with G = {}, Plist = {}, p = {}".format(G,Plist,p))
    n = G.order()
    m = n.prime_to_m_part(p)      # prime-to-p part of order
    if debug:
        print("m={}, n={}".format(m,n))
        print("gens = {}".format(G.gens()))
    if m==n: # p-primary part trivial, nothing to do
        return []

    # project onto p-primary part

    pts  = [m*pt for pt in Plist]
    gens = [m*g.element() for g in G.gens()]
    gens = [g for g in gens if g]
    if debug:
        print("gens for {}-primary part of G: {}".format(p, gens))
        print("{}*points: {}".format(m,pts))
    from sage.groups.generic import discrete_log as dlog
    from sage.modules.all import vector
    Fp = GF(p)

    # If the p-primary part is cyclic we use elliptic discrete logs directly:

    if len(gens) == 1:
        g = gens[0]
        pp = g.order()
        if debug:
            print("Cyclic case, taking dlogs to base {} of order {}".format(g,pp))
        # logs are well-defined mod pp, hence mod p
        v = [dlog(pt, g, ord = pp, operation = '+') for pt in pts]
        if debug:
            print("dlogs: {}".format(v))
        return [vector(Fp,v)]

    # We make no assumption about which generator order divides the
    # other, since conventions differ!

    orders = [g.order() for g in gens]
    p1, p2 = min(orders), max(orders)
    g1, g2 = gens
    if debug:
        print("Non-cyclic case, orders = {}, p1={}, p2={}, g1={}, g2={}".format(orders,p1,p2,g1,g2))

    # Now the p-primary part of the reduction is non-cyclic of
    # exponent p2, and we use the Weil pairing, whose values are p1'th
    # roots of unity with p1|p2, together with discrete log in the
    # multiplicative group.

    zeta = g1.weil_pairing(g2,p2) # a primitive p1'th root of unity
    if debug:
        print("wp of gens = {} with order {}".format(zeta, zeta.multiplicative_order()))
    assert zeta.multiplicative_order() == p1, "Weil pairing error during saturation: p={}, G={}, Plist={}".format(p,G,Plist)

    # logs are well-defined mod p1, hence mod p

    return [vector(Fp, [dlog(pt.weil_pairing(g1,p2), zeta, ord = p1, operation = '*') for pt in pts]),
            vector(Fp, [dlog(pt.weil_pairing(g2,p2), zeta, ord = p1, operation = '*') for pt in pts])]

def p_saturation(Plist, p, sieve=True, lin_combs = dict(), verbose=False):
    r"""
    Checks whether the list of points is `p`-saturated.

    INPUT:

    - ``Plist`` (list) - a list of independent points on one elliptic curve.

    - ``p`` (integer) - a prime number.

    - ``sieve`` (boolean) - if True, use a sieve (when there are at
      least 2 points); otherwise test all combinations.

    - ``lin_combs`` (dict) - a dict, possibly empty, with keys
      coefficient tuples and values the corresponding linear
      combinations of the points in ``Plist``.

    .. note::

       The sieve is much more efficient when the points are saturated
       and the number of points or the prime are large.

    OUTPUT:

    Either (``True``, ``lin_combs``) if the points are `p`-saturated,
    or (``False``, ``i``, ``newP``) if they are not `p`-saturated, in
    which case after replacing the i'th point with ``newP``, the
    subgroup generated contains that generated by ``Plist`` with
    index `p`.  Note that while proving the points `p`-saturated, the
    ``lin_combs`` dict may have been enlarged, so is returned.

    EXAMPLES::

        sage: from sage.schemes.elliptic_curves.saturation import p_saturation
        sage: E = EllipticCurve('389a')
        sage: K.<i> = QuadraticField(-1)
        sage: EK = E.change_ring(K)
        sage: P = EK(1+i,-1-2*i)
        sage: p_saturation([P],2)
        (True, {})
        sage: p_saturation([2*P],2)
        (False, 0, (i + 1 : -2*i - 1 : 1))


        sage: Q = EK(0,0)
        sage: R = EK(-1,1)
        sage: p_saturation([P,Q,R],3)
        (True, {})

    Here we see an example where 19-saturation is proved, with the
    verbose flag set to True so that we can see what is going on::

        sage: p_saturation([P,Q,R],19, verbose=True)
        Using sieve method to saturate...
        E has 19-torsion over Finite Field of size 197, projecting points
         --> [(184 : 27 : 1), (0 : 0 : 1), (196 : 1 : 1)]
         --rank is now 1
        E has 19-torsion over Finite Field of size 197, projecting points
         --> [(15 : 168 : 1), (0 : 0 : 1), (196 : 1 : 1)]
         --rank is now 2
        E has 19-torsion over Finite Field of size 293, projecting points
         --> [(156 : 275 : 1), (0 : 0 : 1), (292 : 1 : 1)]
         --rank is now 3
        Reached full rank: points were 19-saturated
        (True, {})

    An example where the points are not 11-saturated::

        sage: res = p_saturation([P+5*Q,P-6*Q,R],11); res
        (False,
        0,
        (-5783311/14600041*i + 1396143/14600041 : 37679338314/55786756661*i + 3813624227/55786756661 : 1))

    That means that the 0'th point may be replaced by the displayed
    point to achieve an index gain of 11::

        sage: p_saturation([res[2],P-6*Q,R],11)
        (True, {})

    TESTS:

    See :trac:`27387`::

        sage: K.<a> = NumberField(x^2-x-26)
        sage: E = EllipticCurve([a,1-a,0,93-16*a, 3150-560*a])
        sage: P = E([65-35*a/3, (959*a-5377)/9])
        sage: T = E.torsion_points()[0]
        sage: from sage.schemes.elliptic_curves.saturation import p_saturation
        sage: p_saturation([P,T],2,True, {}, True)
        Using sieve method to saturate...
        ...
        -- points were not 2-saturated, gaining index 2
        (False, 0, (-1/4*a + 3/4 : 59/8*a - 317/8 : 1))
        sage: p_saturation([P,T],2,False, {})
        (False, 0, (-1/4*a + 3/4 : 59/8*a - 317/8 : 1))

    """
    # This code does a lot of residue field construction and elliptic curve
    # group structure computations, and would benefit immensely if those
    # were sped up.
    n = len(Plist)
    if n == 0:
        return (True, lin_combs)

    if n == 1 and p == 2:
        try:
            return (False, 0, Plist[0].division_points(p)[0])
        except IndexError:
            return (True, lin_combs)

    E = Plist[0].curve()

    if not sieve:
        from sage.groups.generic import multiples
        from sage.schemes.projective.projective_space import ProjectiveSpace

        mults = [list(multiples(P, p)) for P in Plist[:-1]] + [list(multiples(Plist[-1],2))]
        E0 = E(0)

        for v in ProjectiveSpace(GF(p),n-1): # an iterator
            w = tuple(int(x) for x in v)
            try:
                P = lin_combs[w]
            except KeyError:
                P = sum([m[c] for m,c in zip(mults,w)],E0)
                lin_combs[w] = P
            divisors = P.division_points(p)
            if divisors:
                if verbose:
                    print("  points not saturated at %s, increasing index" % p)
                # w will certainly have a coordinate equal to 1
                return (False, w.index(1), divisors[0])
        # we only get here if no linear combination is divisible by p,
        # so the points are p-saturated:
        return (True, lin_combs)

    # Now we use the more sophisticated sieve to either prove
    # p-saturation, or compute a much smaller list of possible points
    # to test for p-divisibility:

    K = E.base_ring()

    if verbose:
        print("Using sieve method to saturate...")
    from sage.matrix.all import matrix
    from sage.sets.primes import Primes

    A = matrix(GF(p), 0, n)
    rankA = 0
    count = 0
    Edisc = E.discriminant()
    Ediscnorm = Edisc.norm()
    denoms = [P[0].denominator_ideal().norm() for P in Plist]
    Kpol = K.defining_polynomial()
    Kdisc = Kpol.discriminant() # not the disc of K itself

    for q in Primes():
        if q.divides(Ediscnorm) or q.divides(Kdisc) or any(q.divides(pr) for pr in denoms):
            continue
        Fq = GF(q)
        for amodq in Kpol.roots(Fq, multiplicities=False):
            def modq(x):
                try:
                    return x.lift().change_ring(Fq)(amodq)
                except AttributeError: # in case x is in QQ
                    return Fq(x)
            from sage.all import EllipticCurve
            Ek = EllipticCurve([modq(a) for a in E.ainvs()])
            # computing cardinality faster than computing abelian group
            if not p.divides(Ek.cardinality()):
                # if verbose:
                #     print("E over %s: no %s-torsion, skipping" % (Fq,p))
                continue
            if verbose:
                print("E has %s-torsion over %s, projecting points" % (p,Fq))
            projPlist = [Ek([modq(c) for c in pt]) for pt in Plist]
            if verbose:
                print(" --> %s" % projPlist)

            G = Ek.abelian_group()
            try:
                vecs = p_projections(G, projPlist, p)
            except ValueError:
                try:
                    vecs = p_projections(G, projPlist, p, debug=True)
                except ValueError:
                    vecs = []
            for v in vecs:
                A = matrix(A.rows()+[v])
            newrank = A.rank()
            if verbose:
                print(" --rank is now %s" % newrank)
            if newrank == n:
                if verbose:
                    print("Reached full rank: points were %s-saturated" % p)
                return (True, lin_combs)
            if newrank == rankA:
                count += 1
                if count == 10:
                    if verbose:
                        print("! rank same for 10 steps, checking kernel...")
                    # no increase in rank for the last 10 primes Q
                    # find the points in the kernel and call the no-sieve version
                    vecs = A.right_kernel().basis()
                    if verbose:
                        print("kernel vectors: %s" % vecs)
                    Rlist = [sum([int(vi)*Pi for vi,Pi in zip(v,Plist)],E(0))
                             for v in vecs]
                    if verbose:
                        print("points generating kernel: %s" % Rlist)

                    res = p_saturation(Rlist, p, sieve=False, lin_combs = dict(), verbose=verbose)
                    if res[0]: # points really were saturated
                        if verbose:
                            print("-- points were %s-saturated" % p)
                        return (True, lin_combs)
                    else: # they were not, and Rlist[res[1]] can be
                        # replaced by res[2] to enlarge the span; we
                        # need to find a point in Plist which can be
                        # replaced: any one with a nonzero coordinate in
                        # the appropriate kernel vector will do.
                        if verbose:
                            print("-- points were not %s-saturated, gaining index %s" % (p,p))
                        j = next(i for i,x in enumerate(vecs[res[1]]) if x)
                        return (False, j, res[2])
                else: # rank stayed same; carry on using more Qs
                    pass
            else: # rank went up but is <n; carry on using more Qs
                rankA = newrank
                count = 0

    # We reach here only if using many auxiliary primes Q, the
    # rank never stuck for 10 consecutive Qs but is still < n.  That
    # means that n is rather large, or perhaps that E has a large
    # number of bad primes.  So we fall back to the naive method,
    # still making use of any partial information about the kernel we
    # have acquired.

    vecs = A.right_kernel().basis()
    Rlist = [sum([int(vi)*Pi for vi,Pi in zip(v,Plist)],E(0))
             for v in vecs]
    res = p_saturation(Rlist, p, sieve=False, lin_combs = dict(), verbose=verbose)
    if res[0]: # points really were saturated
        return (True, lin_combs)
    else:
        j = next(i for i, x in enumerate(vecs[res[1]]) if x)
        return (False, j, res[2])


def full_p_saturation(Plist, p, lin_combs = dict(), verbose=False):
    r"""
    Full `p`-saturation of ``Plist``.

    INPUT:

    - ``Plist`` (list) - a list of independent points on one elliptic curve.

    - ``p`` (integer) - a prime number.

    - ``lin_combs`` (dict, default null) - a dict, possibly empty,
      with keys coefficient tuples and values the corresponding linear
      combinations of the points in ``Plist``.

    OUTPUT:

    (``newPlist``, exponent) where ``newPlist`` has the same length as
    ``Plist`` and spans the `p`-saturation of the span of ``Plist``,
    which contains that span with index ``p**exponent``.

    EXAMPLES::

        sage: from sage.schemes.elliptic_curves.saturation import full_p_saturation
        sage: E = EllipticCurve('389a')
        sage: K.<i> = QuadraticField(-1)
        sage: EK = E.change_ring(K)
        sage: P = EK(1+i,-1-2*i)
        sage: full_p_saturation([8*P],2,verbose=True)
         --starting full 2-saturation
        Points were not 2-saturated, exponent was 3
        ([(i + 1 : -2*i - 1 : 1)], 3)

        sage: Q = EK(0,0)
        sage: R = EK(-1,1)
        sage: full_p_saturation([P,Q,R],3)
        ([(i + 1 : -2*i - 1 : 1), (0 : 0 : 1), (-1 : 1 : 1)], 0)

    An example where the points are not 7-saturated and we gain index
    exponent 1.  Running this example with verbose=True shows that it
    uses the code for when the reduction has p-rank 2 (which occurs
    for the reduction modulo `(16-5i)`), which uses the Weil pairing::

        sage: full_p_saturation([P,Q+3*R,Q-4*R],7)
        ([(i + 1 : -2*i - 1 : 1),
        (2869/676 : 154413/17576 : 1),
        (-7095/502681 : -366258864/356400829 : 1)],
        1)

    """
    if not Plist:
        return Plist, ZZ.zero()

    exponent = ZZ(0)

    # To handle p-torsion, we must add any torsion generators whose
    # order is divisible by p to the list of points.  Note that it is
    # not correct to add generators of the p-torsion here, we actually
    # need generators of p-cotorsion.  If there are any of these, we
    # cannot use the supplied dict of linear combinations, so we reset
    # this.  The torsion points are removed before returning the
    # saturated list.

    if verbose:
        print(" --starting full %s-saturation"  % p)

    n = len(Plist) # number of points supplied & to be returned
    nx = n         # number of points including relevant torsion
    E = Plist[0].curve()
    Tgens = E.torsion_subgroup().gens()
    for T in Tgens:
        if p.divides(T.order()):
            # NB The following line creates a new list of points,
            # which is essential.  If it is replaced by Plist+=[T]
            # then while this function would return the correct
            # output, there would be a very bad side effect: the
            # caller's list would have been changed here.
            Plist = Plist + [T.element()]
            nx += 1
    extra_torsion = nx-n
    if extra_torsion:
        lin_combs = dict()
        if verbose:
            print("Adding %s torsion generators before %s-saturation"
                  % (extra_torsion,p))

    res = p_saturation(Plist, p, True, lin_combs, verbose)
    while not res[0]:
        exponent += 1
        Plist[res[1]] = res[2]
        res = p_saturation(Plist, p, True, lin_combs, verbose)

    if extra_torsion:
        # remove the torsion points
        if verbose:
            print("Removing the torsion generators after %s-saturation" % p)
        Plist = Plist[:n]

    if verbose:
        if exponent:
            print("Points were not %s-saturated, exponent was %s" % (p,exponent))
        else:
            print("Points were %s-saturated" % p)

    return (Plist, exponent)
