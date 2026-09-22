# -*- coding: utf-8 -*-
"""Vectorise le logo fidelement a son PNG.

  - la forme  : contour de l'alpha a mi-couverture (marching squares, interpole)
  - la touche : la jambe gauche du signe, redessinee par-dessus en caramel
  - l'ombre   : des courbes de niveau de la luminance, empilees du clair au
    sombre, chacune en noir translucide. On ne modelise rien : on suit ce que
    le pixel dit, donc le pli garde son arete nette et ne bave nulle part.
  La base reste recolorable (--wrangle-ink), la touche aussi (--wrangle-acc) :
  l'ombre est du noir a opacite variable posee dessus, bornee a la silhouette.

Le PNG est decode ici meme, avec zlib et rien d'autre : le depot n'embarque
aucune bibliotheque d'images, et il n'en faut pas pour lire huit bits par
canal sans entrelacement.

  py vectoriser2.py [sortie.svg] [source.png]
  py vectoriser2.py [sortie.svg] [source.png] --ecraser

Les reglages ci-dessous (tolerances, flou, nombre de niveaux) ont ete accordes
sur une source large d'environ 1500 px. Une source nettement plus grande ou
plus petite donnera un rendu comparable mais pas identique.
"""
import math
import os
import re
import sys
import zlib

ICI = os.path.dirname(os.path.abspath(__file__))
# Les chemins se deduisent de l'emplacement du script : le dossier du projet
# peut etre deplace ou renomme sans rien casser ici.
OPTIONS = [a for a in sys.argv[1:] if a.startswith('--')]
RESTE = [a for a in sys.argv[1:] if not a.startswith('--')]
SORTIE = RESTE[0] if RESTE else os.path.join(ICI, 'public', 'wrangle-logo.svg')
SOURCE = RESTE[1] if len(RESTE) > 1 else os.path.join(ICI, 'public', 'wrangle-logo.png')
ECRASER = '--ecraser' in OPTIONS
TOL_FORME = 0.30     # simplification de la silhouette (px)
# La seule couleur du logo, celle du caramel de la feuille de style (--acc).
# Ce n'est qu'un repli : la page pose --wrangle-acc et decide.
ACCENT = '#E7B04A'
# Au-dela de cette abscisse, c'est le mot : il est plat (249..255), on n'y
# touche pas. En fraction de la largeur — le creux entre le signe et le mot —
# pour que le reperage suive la taille de la source.
X_MOT = 780 / 1569
# L'ombre se lit en deux temps : l'ambiance, tres douce, qu'un flou large lisse
# sans risque ; puis le pli, franc, qu'on garde net pour ne pas perdre son arete.
# Beaucoup de niveaux plutot qu'un flou fort : le flou, applique avant le
# detourage, rongerait l'arete du pli, la ou l'ombre est justement la plus dense.
AMBIANCE = dict(nom='ambiance', niveaux=list(range(253, 233, -2)), tol=1.5, flou=3.0)
PLI      = dict(nom='pli', niveaux=[231, 226, 221, 216, 211, 206, 201, 196, 191, 186, 181,
                                    176, 171, 166, 161, 156, 151, 146, 141, 137], tol=0.5, flou=0.4)
REGLAGES = (AMBIANCE, PLI)


# ------------------------------------------------- lecture du PNG

def paeth(a, b, c):
    """Le predicteur de PNG : des trois voisins, celui qui est le plus proche
    de a + b - c (gauche, dessus, diagonale haut-gauche)."""
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def defiltrer(brut, w, h, canaux):
    """Chaque rangee d'un PNG est precedee du filtre qui l'encode : on la remet
    a plat. Le test porte sur la rangee, pas sur l'octet : c'est ce qui rend la
    boucle tenable en Python sur plusieurs millions de pixels."""
    large = w * canaux
    sortie = bytearray(h * large)
    prec = bytearray(large)
    pos = 0
    for j in range(h):
        filtre = brut[pos]
        cur = bytearray(brut[pos + 1:pos + 1 + large])
        pos += 1 + large
        if filtre == 1:            # Sub : le pixel de gauche
            for k in range(canaux, large):
                cur[k] = (cur[k] + cur[k - canaux]) & 255
        elif filtre == 2:          # Up : le pixel du dessus
            for k in range(large):
                cur[k] = (cur[k] + prec[k]) & 255
        elif filtre == 3:          # Average : la moyenne des deux
            for k in range(large):
                g = cur[k - canaux] if k >= canaux else 0
                cur[k] = (cur[k] + ((g + prec[k]) >> 1)) & 255
        elif filtre == 4:          # Paeth
            for k in range(large):
                g = cur[k - canaux] if k >= canaux else 0
                hg = prec[k - canaux] if k >= canaux else 0
                cur[k] = (cur[k] + paeth(g, prec[k], hg)) & 255
        elif filtre:
            raise SystemExit('filtre PNG %d inconnu a la rangee %d' % (filtre, j))
        sortie[j * large:(j + 1) * large] = cur
        prec = cur
    return sortie


def png(chemin):
    """Le PNG en largeur, hauteur, nombre de canaux et octets defiltres.
    Huit bits par canal, sans palette ni entrelacement : ce que produit
    n'importe quel export de logo."""
    try:
        with open(chemin, 'rb') as f:
            brut = f.read()
    except OSError as e:
        raise SystemExit('source illisible : %s (%s)' % (chemin, e))
    if brut[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('%s n est pas un PNG' % chemin)
    w = h = canaux = 0
    compresse = bytearray()
    i = 8
    while i + 8 <= len(brut):
        n = int.from_bytes(brut[i:i + 4], 'big')
        genre = brut[i + 4:i + 8]
        corps = brut[i + 8:i + 8 + n]
        if genre == b'IHDR':
            w = int.from_bytes(corps[0:4], 'big')
            h = int.from_bytes(corps[4:8], 'big')
            profondeur, couleur, _, _, entrelace = corps[8:13]
            canaux = {0: 1, 2: 3, 4: 2, 6: 4}.get(couleur, 0)
            if profondeur != 8 or not canaux or entrelace:
                raise SystemExit('PNG 8 bits, sans palette ni entrelacement, attendu '
                                 '(profondeur %d, couleur %d, entrelace %d)'
                                 % (profondeur, couleur, entrelace))
        elif genre == b'IDAT':
            compresse += corps
        elif genre == b'IEND':
            break
        i += 12 + n            # longueur, genre, corps, controle
    if not (w and h and compresse):
        raise SystemExit('%s : PNG incomplet' % chemin)
    return w, h, canaux, defiltrer(zlib.decompress(bytes(compresse)), w, h, canaux)


def garde_cadre(sortie, w, h):
    """Le logo deja en place a-t-il le meme cadre que la source ?

    La page appelle le logo dans un viewBox ecrit en dur (`class="marque"` dans
    wrangle.html) et l'icone d'onglet reprend les memes coordonnees. Un logo
    regenere a d'autres proportions y serait rogne, sans rien dire. Plutot que
    d'abimer la page, on s'arrete et on explique."""
    if ECRASER or not os.path.exists(sortie):
        return
    try:
        with open(sortie, encoding='utf-8') as f:
            tete = f.read(400)
    except OSError:
        return
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', tete)
    if not m or (int(m.group(1)), int(m.group(2))) == (w, h):
        return
    raise SystemExit(
        'ARRET : le logo en place est en %s x %s, la source en %d x %d.\n'
        '        La page appelle le logo dans un viewBox ecrit en dur : le\n'
        '        regenerer a d autres proportions le rognerait en silence.\n'
        '        Donner la source d origine, ecrire ailleurs, ou passer\n'
        '        --ecraser et corriger le viewBox de wrangle.html a la main.'
        % (m.group(1), m.group(2), w, h))


def plans(w, h, canaux, px):
    """Les deux champs que lit la suite : l'opacite et la luminance de chaque
    pixel. Luminance ITU-R BT.601, celle des passages en niveaux de gris."""
    plein = bytearray([255]) * (w * h)
    if canaux >= 3:
        lum = bytearray((r * 299 + v * 587 + b * 114) // 1000
                        for r, v, b in zip(px[0::canaux], px[1::canaux], px[2::canaux]))
        return (bytearray(px[3::canaux]) if canaux == 4 else plein), lum
    return (bytearray(px[1::canaux]) if canaux == 2 else plein), bytearray(px[0::canaux])


# ------------------------------------------------- marching squares

def contours(F, w, h, iso):
    """Le trait de niveau `iso` du champ F, en segments. Les booleens d'une
    rangee servent deux fois — bas d'une cellule puis haut de la suivante — et
    les valeurs ne sont relues que pour les cellules que le trait traverse :
    l'immense majorite est uniforme et ne coute qu'une comparaison."""
    segs = []

    def interp(x0, y0, v0, x1, y1, v1):
        t = (iso - v0) / (v1 - v0)
        return (round(x0 + (x1 - x0) * t, 3), round(y0 + (y1 - y0) * t, 3))

    haut = [v >= iso for v in F[:w]]
    for j in range(h - 1):
        r0, r1 = j * w, (j + 1) * w
        bas = [v >= iso for v in F[r1:r1 + w]]
        for i in range(w - 1):
            ia, ib, id_, ic = haut[i], haut[i + 1], bas[i], bas[i + 1]
            if ia == ib == ic == id_:
                continue
            a, b, c, d = F[r0 + i], F[r0 + i + 1], F[r1 + i + 1], F[r1 + i]
            x, y = i + .5, j + .5
            top = interp(x, y, a, x + 1, y, b) if ia != ib else None
            rgt = interp(x + 1, y, b, x + 1, y + 1, c) if ib != ic else None
            bot = interp(x, y + 1, d, x + 1, y + 1, c) if id_ != ic else None
            lft = interp(x, y, a, x, y + 1, d) if ia != id_ else None
            pts = [p for p in (top, rgt, bot, lft) if p]
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif ia == ((a + b + c + d) / 4.0 >= iso):
                segs.append((top, rgt)); segs.append((bot, lft))
            else:
                segs.append((top, lft)); segs.append((rgt, bot))
        haut = bas
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


def chemins(loops, tol, dec=1):
    """Chaque boucle simplifiee : son attribut `d`, son nombre de points et son
    abscisse la plus a gauche. Une boucle qui tombe sous trois points ne dessine
    rien, elle est laissee."""
    f = '%.{}f'.format(dec)
    out = []
    for lp in loops:
        s = simplifier_boucle(lp, tol)
        if len(s) >= 3:
            out.append(('M' + ' L'.join(f % p[0] + ' ' + f % p[1] for p in s) + 'Z',
                        len(s), min(p[0] for p in s)))
    return out


def chemin(loops, tol, dec=1):
    """Toutes les boucles en un seul attribut `d`, et le nombre de points ecrits."""
    parts = chemins(loops, tol, dec)
    return ' '.join(p[0] for p in parts), sum(p[1] for p in parts)


# ------------------------------------------------- main

w, h, canaux, px = png(SOURCE)
garde_cadre(SORTIE, w, h)
A, L = plans(w, h, canaux, px)
x_mot = round(X_MOT * w)
clairs = sorted(L[i] for i in range(w * h) if A[i] >= 250 and L[i] >= 246)
if not clairs:
    raise SystemExit('%s : aucun pixel opaque et clair, ce n est pas le logo' % SOURCE)
BASE = clairs[len(clairs) // 2]

# 1. la silhouette, et dans ses boucles celle du trait le plus a gauche : la
#    jambe gauche du signe, la seule que le logo porte en couleur. On la repere
#    a son abscisse et non a son rang, pour que l'ordre des boucles n'ait pas
#    a etre stable.
formes = chemins(boucles(contours(A, w, h, 127.5)), TOL_FORME)
if not formes:
    raise SystemExit('%s : aucune silhouette, ce n est pas le logo' % SOURCE)
d_forme = ' '.join(p[0] for p in formes)
n_forme = sum(p[1] for p in formes)
d_accent, n_accent, _ = min(formes, key=lambda p: p[2])

# 2. l'ombre, en courbes de niveau relevees sur le seul signe. Hors de la forme
#    et sur le mot, le champ vaut 255 : les niveaux se ferment proprement.
champ = [L[i] if (A[i] >= 200 and i % w < x_mot) else 255 for i in range(w * h)]
LMIN = min(L[i] for i in range(w * h) if A[i] >= 250 and i % w < x_mot)
tous = [n for r in REGLAGES for n in r['niveaux']] + [LMIN]
# le niveau qui suit chacun : c'est lui qui donne le milieu de la bande
suivant = {n: tous[k + 1] for k, n in enumerate(tous[:-1])}
groupes, alpha_cumul = [], 0.0
for reglage in REGLAGES:
    bandes = []
    for niveau in reglage['niveaux']:
        lps = boucles(contours(champ, w, h, niveau), mini=20)
        if not lps:
            continue
        d, n = chemin(lps, reglage['tol'])
        # une bande couvre de ce niveau au suivant : on vise sa luminance
        # mediane, sans quoi tout l'ombrage serait clair d'un demi-palier
        cible = max(0.0, 1 - ((niveau + suivant[niveau]) / 2.0) / float(BASE))
        pas = (cible - alpha_cumul) / (1 - alpha_cumul)  # ce qu'il reste a poser
        if pas <= 0.002:
            continue
        alpha_cumul = cible
        bandes.append(dict(d=d, pas=pas, niveau=niveau, points=n, boucles=len(lps)))
    groupes.append(dict(nom=reglage['nom'], flou=reglage['flou'], bandes=bandes))

hexbase = '#%02X%02X%02X' % (BASE, BASE, BASE)
out = ['<svg id="wrangle" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
       'role="img" aria-label="Wrangle">' % (w, h, w, h),
       '  <title>Wrangle</title>',
       '  <defs>',
       '    <clipPath id="wg-forme"><path d="%s"/></clipPath>' % d_forme,
       ]
for k, g in enumerate(groupes):
    out.append('    <filter id="wg-f%d" x="-3%%" y="-8%%" width="106%%" height="116%%">'
               '<feGaussianBlur stdDeviation="%s"/></filter>' % (k, g['flou']))
out += ['  </defs>',
        '  <path fill-rule="evenodd" style="fill:var(--wrangle-ink,%s)" d="%s"/>' % (hexbase, d_forme),
        '  <!-- la touche caramel : le trait gauche du signe, par-dessus la base (variable wrangle-acc) -->',
        '  <path style="fill:var(--wrangle-acc,%s)" d="%s"/>' % (ACCENT, d_accent),
        '  <!-- l ombre : des courbes de niveau relevees sur l image, du clair au',
        '       sombre, en noir translucide. La base dessous reste recolorable. -->']
for k, g in enumerate(groupes):
    out.append('  <g clip-path="url(#wg-forme)" filter="url(#wg-f%d)" fill="#000" fill-rule="evenodd">' % k)
    for b in g['bandes']:
        out.append('    <path fill-opacity="%.3f" d="%s"/>' % (b['pas'], b['d']))
    out.append('  </g>')
out += ['</svg>', '']
with open(SORTIE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('source    : %s (%d x %d, %d canaux)' % (SOURCE, w, h, canaux))
print('base      : %s' % hexbase)
print('silhouette: %d boucles, %d points (tol %.2f)' % (len(formes), n_forme, TOL_FORME))
print('touche    : %d points, repli %s' % (n_accent, ACCENT))
for g in groupes:
    print('%-8s (flou %.1f) :' % (g['nom'], g['flou']))
    for b in g['bandes']:
        print('   niveau %3d : %2d boucle(s), %4d points, opacite +%.3f'
              % (b['niveau'], b['boucles'], b['points'], b['pas']))
print('fichier   : %s (%.1f Ko)' % (SORTIE, os.path.getsize(SORTIE) / 1024.0))
