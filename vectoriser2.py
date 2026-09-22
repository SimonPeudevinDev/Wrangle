# -*- coding: utf-8 -*-
"""Vectorise le logo fidelement au PNG.

  - la forme  : contour de l'alpha a mi-couverture (marching squares, interpole)
  - l'ombre   : des courbes de niveau de la luminance, empilees du clair au
    sombre, chacune en noir translucide. On ne modelise rien : on suit ce que
    le pixel dit, donc le pli garde son arete nette et ne bave nulle part.
  La base reste recolorable (--wrangle-ink) : l'ombre est du noir a opacite
  variable posee dessus, bornee a la silhouette.
"""
import io, math, os, sys

S = ('C:/Users/SIMON~1.PEU/AppData/Local/Temp/claude/d--DIT-Log/'
     '7501c739-d19e-4a22-9594-0015d01cc9c2/scratchpad')
SORTIE = sys.argv[1] if len(sys.argv) > 1 else 'D:/DIT-Log/public/wrangle-logo.svg'
TOL_FORME = 0.30     # simplification de la silhouette (px)
X_MOT = 780          # au-dela, c'est le mot : il est plat (249..255), on n'y touche pas
# L'ombre se lit en deux temps : l'ambiance, tres douce, qu'un flou large lisse
# sans risque ; puis le pli, franc, qu'on garde net pour ne pas perdre son arete.
# Beaucoup de niveaux plutot qu'un flou fort : le flou, applique avant le
# detourage, rongerait l'arete du pli, la ou l'ombre est justement la plus dense.
AMBIANCE = dict(niveaux=list(range(253, 233, -2)), tol=1.5, flou=3.0)
PLI      = dict(niveaux=[231, 226, 221, 216, 211, 206, 201, 196, 191, 186, 181,
                         176, 171, 166, 161, 156, 151, 146, 141, 137], tol=0.5, flou=0.4)


def pgm(p):
    tok = open(p, 'rb').read().split()
    w, h = int(tok[1]), int(tok[2])
    return w, h, [int(v) for v in tok[4:4 + w * h]]


# ------------------------------------------------- marching squares

def contours(F, w, h, iso):
    segs = []
    def interp(x0, y0, v0, x1, y1, v1):
        t = (iso - v0) / (v1 - v0)
        return (round(x0 + (x1 - x0) * t, 3), round(y0 + (y1 - y0) * t, 3))
    for j in range(h - 1):
        r0, r1 = j * w, (j + 1) * w
        for i in range(w - 1):
            a, b, c, d = F[r0 + i], F[r0 + i + 1], F[r1 + i + 1], F[r1 + i]
            ia, ib, ic, id_ = a >= iso, b >= iso, c >= iso, d >= iso
            if ia == ib == ic == id_:
                continue
            x, y = i + .5, j + .5
            top = interp(x, y, a, x + 1, y, b) if ia != ib else None
            rgt = interp(x + 1, y, b, x + 1, y + 1, c) if ib != ic else None
            bot = interp(x, y + 1, d, x + 1, y + 1, c) if id_ != ic else None
            lft = interp(x, y, a, x, y + 1, d) if ia != id_ else None
            pts = [p for p in (top, rgt, bot, lft) if p]
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            else:
                if ia == ((a + b + c + d) / 4.0 >= iso):
                    segs.append((top, rgt)); segs.append((bot, lft))
                else:
                    segs.append((top, lft)); segs.append((rgt, bot))
    return segs


def boucles(segs, mini=8):
    voisins = {}
    for k, (p, q) in enumerate(segs):
        voisins.setdefault(p, []).append(k)
        voisins.setdefault(q, []).append(k)
    vus = [False] * len(segs)
    out = []
    for k0 in range(len(segs)):
        if vus[k0]:
            continue
        p, q = segs[k0]
        vus[k0] = True
        chaine, cur = [p, q], q
        while True:
            suiv = next((k for k in voisins.get(cur, []) if not vus[k]), None)
            if suiv is None:
                break
            vus[suiv] = True
            a, b = segs[suiv]
            cur = b if a == cur else a
            if cur == chaine[0]:
                break
            chaine.append(cur)
        if len(chaine) >= mini:
            out.append(chaine)
    return out


# ------------------------------------------------- simplification

def dist_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    pile, garde = [(0, len(pts) - 1)], [False] * len(pts)
    garde[0] = garde[-1] = True
    while pile:
        i0, i1 = pile.pop()
        a, b = pts[i0], pts[i1]
        imax, dmax = -1, tol
        for i in range(i0 + 1, i1):
            d = dist_seg(pts[i], a, b)
            if d > dmax:
                imax, dmax = i, d
        if imax > 0:
            garde[imax] = True
            pile.append((i0, imax)); pile.append((imax, i1))
    return [p for p, g in zip(pts, garde) if g]


def simplifier_boucle(pts, tol):
    p0 = pts[0]
    k = max(range(len(pts)), key=lambda i: (pts[i][0] - p0[0]) ** 2 + (pts[i][1] - p0[1]) ** 2)
    m1 = dp(pts[:k + 1], tol)
    m2 = dp(pts[k:] + [p0], tol)
    return m1[:-1] + m2[:-1]


def chemin(loops, tol, dec=1):
    f = '%.{}f'.format(dec)
    d = []
    for lp in loops:
        s = simplifier_boucle(lp, tol)
        if len(s) >= 3:
            d.append('M' + ' L'.join(f % p[0] + ' ' + f % p[1] for p in s) + 'Z')
    return ' '.join(d), sum(len(simplifier_boucle(l, tol)) for l in loops)


# ------------------------------------------------- main

w, h, A = pgm(os.path.join(S, 'alpha.pgm'))
_, _, L = pgm(os.path.join(S, 'lum.pgm'))
clairs = sorted(L[i] for i in range(w * h) if A[i] >= 250 and L[i] >= 246)
BASE = clairs[len(clairs) // 2]

# 1. la silhouette
d_forme, n_forme = chemin(boucles(contours(A, w, h, 127.5)), TOL_FORME)

# 2. l'ombre, en courbes de niveau relevees sur le seul signe. Hors de la forme
#    et sur le mot, le champ vaut 255 : les niveaux se ferment proprement.
champ = [L[i] if (A[i] >= 200 and i % w < X_MOT) else 255 for i in range(w * h)]
LMIN = min(L[i] for i in range(w * h) if A[i] >= 250 and i % w < X_MOT)
tous = [n for r in (AMBIANCE, PLI) for n in r['niveaux']] + [LMIN]
groupes, alpha_cumul = [], 0.0
for reglage in (AMBIANCE, PLI):
    bandes = []
    for niveau in reglage['niveaux']:
        lps = boucles(contours(champ, w, h, niveau), mini=20)
        if not lps:
            continue
        d, n = chemin(lps, reglage['tol'])
        # une bande couvre de ce niveau au suivant : on vise sa luminance
        # mediane, sans quoi tout l'ombrage serait clair d'un demi-palier
        milieu = (niveau + tous[tous.index(niveau) + 1]) / 2.0
        cible = max(0.0, 1 - milieu / float(BASE))
        pas = (cible - alpha_cumul) / (1 - alpha_cumul)  # ce qu'il reste a poser
        if pas <= 0.002:
            continue
        alpha_cumul = cible
        bandes.append((d, pas, niveau, n, len(lps)))
    groupes.append((reglage['flou'], bandes))

hexbase = '#%02X%02X%02X' % (BASE, BASE, BASE)
out = ['<svg id="wrangle" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
       'role="img" aria-label="Wrangle">' % (w, h, w, h),
       '  <title>Wrangle</title>',
       '  <defs>',
       '    <clipPath id="wg-forme"><path d="%s"/></clipPath>' % d_forme,
       ]
for k, (flou, _) in enumerate(groupes):
    out.append('    <filter id="wg-f%d" x="-3%%" y="-8%%" width="106%%" height="116%%">'
               '<feGaussianBlur stdDeviation="%s"/></filter>' % (k, flou))
out += ['  </defs>',
       '  <path fill-rule="evenodd" style="fill:var(--wrangle-ink,%s)" d="%s"/>' % (hexbase, d_forme),
       '  <!-- l ombre : des courbes de niveau relevees sur l image, du clair au',
       '       sombre, en noir translucide. La base dessous reste recolorable. -->']
for k, (flou, bandes) in enumerate(groupes):
    out.append('  <g clip-path="url(#wg-forme)" filter="url(#wg-f%d)" fill="#000" fill-rule="evenodd">' % k)
    for d, pas, niveau, n, nb in bandes:
        out.append('    <path fill-opacity="%.3f" d="%s"/>' % (pas, d))
    out.append('  </g>')
out += ['</svg>', '']
svg = '\n'.join(out)
io.open(SORTIE, 'w', encoding='utf-8').write(svg)

print('base      : %s' % hexbase)
print('silhouette: %d points (tol %.2f)' % (n_forme, TOL_FORME))
for k, (flou, bandes) in enumerate(groupes):
    print('%s (flou %.1f) :' % ('ambiance' if k == 0 else 'pli    ', flou))
    for d, pas, niveau, n, nb in bandes:
        print('   niveau %3d : %2d boucle(s), %4d points, opacite +%.3f' % (niveau, nb, n, pas))
print('fichier   : %s (%.1f Ko)' % (SORTIE, os.path.getsize(SORTIE) / 1024.0))
