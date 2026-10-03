# -*- coding: utf-8 -*-
"""Le croquis tourne sous deux doigts : pincer zoome, tourner tourne la feuille.

Le point tenu reste sous les doigts, un trait pose apres la rotation tombe la ou
le doigt touche, la feuille se colle aux quarts de tour, un pincement seul ne la
fait pas tourner, et « 100 % » la remet droite.

  py tests/verif_tourner.py
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais()
with Banc(8797, 9382) as banc:
    banc.ouvrir()
    banc.nommer()
    banc.js("UI.rotCroquis = 0; ecrireUI()")
    banc.js('ouvrirCroquis(DB.plans[0].id)'); time.sleep(0.8)

    # deux doigts autour du centre de la zone, a 200 px l'un de l'autre
    banc.js("""
      window.geste = (pas) => {
        const z = $('dzone').getBoundingClientRect(), cx = z.left + z.width / 2, cy = z.top + z.height / 2;
        const ev = (id, x, y) => ({ pointerId:id, clientX:x, clientY:y });
        doigtPose(ev(1, cx - 100, cy)); doigtPose(ev(2, cx + 100, cy));
        const tenu = pince.pt.slice();
        for (const [ang, d] of pas){
          const r = ang * Math.PI / 180;
          doigtBouge(ev(1, cx - d * Math.cos(r), cy - d * Math.sin(r)));
          doigtBouge(ev(2, cx + d * Math.cos(r), cy + d * Math.sin(r)));
        }
        const sous = feuilleSous(cx, cy);
        doigtLeve(ev(1)); doigtLeve(ev(2));
        return { rot: dessin.rot, zoom: dessin.zoom, ecart: Math.hypot(sous[0] - tenu[0], sous[1] - tenu[1]) };
      };
    """)

    r = banc.js("geste([[2, 100], [4, 160]])")
    essais.verifier('un pincement seul : la feuille ne tourne pas', r['rot'], 0)
    essais.verifier('un pincement seul : elle zoome', round(r['zoom'], 2), 1.6)

    r = banc.js("geste([[15, 100], [30, 100], [40, 100]])")
    essais.verifier('tourner de 40 degres : la feuille suit, moins le seuil', round(r['rot']), 28)
    essais.verifier('le point tenu reste sous les doigts (a moins de 2 unites)', r['ecart'] < 2, True)
    essais.verifier('l angle s affiche a cote du zoom', banc.js("$('dzoom').textContent"), '160 % · 28°')

    # un point de la feuille, la ou l'ecran le montre : le canevas tourne en CSS et pointCroquis doit s'accorder
    juste = banc.js("""
      (() => { const c = $('croquis'), r = c.getBoundingClientRect(), k = c.offsetWidth / dessin.w, a = dessin.rot * Math.PI / 180;
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2, ox = (300 - dessin.w / 2) * k, oy = (200 - dessin.h / 2) * k;
        return pointCroquis({ clientX: cx + ox * Math.cos(a) - oy * Math.sin(a), clientY: cy + ox * Math.sin(a) + oy * Math.cos(a) }); })()
    """)
    essais.verifier('sous la feuille de travers, le doigt touche le bon point', all(abs(v - w) <= 1 for v, w in zip(juste, [300, 200])), True)

    r = banc.js("geste([[20, 100], [50, 100], [72, 100]])")
    essais.verifier('a 2 degres d un quart de tour : la feuille s y colle', r['rot'], 90)
    essais.verifier('reposee droite : l appareil s en souvient', banc.js('UI.rotCroquis'), 90)

    banc.js("dessin.rot = 37; pivoterCroquis()")
    essais.verifier('le bouton pivoter repart du quart de tour suivant', banc.js('dessin.rot'), 90)

    banc.js("dessin.rot = 37; zoomCroquis(null)")
    essais.verifier('100 % : la feuille revient droite, en vue entiere', [banc.js('dessin.rot'), banc.js('dessin.zoom'), banc.js("$('dzoom').textContent")], [90, 1, '100 %'])

    essais.exceptions(banc)
essais.bilan()
