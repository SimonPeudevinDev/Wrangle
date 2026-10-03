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

    # -- les objets : chacun a son anneau pour tourner et son carre pour la taille
    banc.js("""
      outilCroquis('move');
      window.tirer = (o, quoi, vers) => {
        dessin.selection = o;
        const p = poigneesDe(o).find(q => q[quoi]), ev = (x, y) => ({ pointerId:9, button:0, buttons:1, clientX:0, clientY:0, preventDefault(){}, currentTarget:{ setPointerCapture(){} } });
        const garde = pointCroquis; pointCroquis = () => [p.x, p.y]; debutTrait(ev());
        pointCroquis = () => vers; mouvTrait(ev()); pointCroquis = garde; finTrait(ev());
      };
    """)
    for t in ['bloc', 'rond', 'trajet', 'trait', 'txt', 'cam']:
        r = banc.js("""(() => {
          const t = '%s', n = ++dessin.seq;
          const o = t === 'trait' ? { c:'#000', w:3, n, pts:[[400,400],[600,400]] }
                  : t === 'trajet' ? { t, n, pts:[[400,400],[500,420],[600,400]] }
                  : t === 'txt' ? { t, n, x:400, y:400, txt:'Hello' }
                  : t === 'cam' ? { t, n, x:500, y:400, a:0 }
                  : { t, n, x1:400, y1:350, x2:600, y2:450 };
          (t === 'trait' ? dessin.traits : dessin.objets).push(o);
          const h = poigneesDe(o);
          return { rot: h.some(q => q.rot), taille: h.some(q => q.taille) }; })()""" % t)
        essais.verifier(t + ' : un anneau pour tourner, un carre pour la taille', [r['rot'], r['taille']], [True, True])

    r = banc.js("""(() => { const o = dessin.traits[dessin.traits.length - 1]; tirer(o, 'rot', [800, 410]);
      return o.pts.map(q => q.map(Math.round)); })()""")
    essais.verifier('le trait tourne d un quart de tour autour de son centre (cran a 45 degres)', r, [[500, 300], [500, 500]])
    r = banc.js("""(() => { const o = dessin.traits[dessin.traits.length - 1]; const p = poigneesDe(o).find(q => q.taille);
      const d = Math.hypot(p.x - 500, p.y - 400); tirer(o, 'taille', [500 + (p.x - 500) * 2, 400 + (p.y - 400) * 2]);
      return o.pts.map(q => q.map(Math.round)); })()""")
    essais.verifier('le trait double de taille', r, [[500, 200], [500, 600]])
    r = banc.js("""(() => { const o = dessin.objets.find(x => x.t === 'bloc'); tirer(o, 'taille', [700, 300]);
      return [o.x1, o.y1, o.x2, o.y2]; })()""")
    essais.verifier('le coin du bloc tire sa largeur et sa hauteur, autour du centre', r, [300, 300, 700, 500])
    essais.verifier('annuler rend le bloc d avant', banc.js("annulerTrait(); (o => [o.x1, o.x2])(dessin.objets.find(x => x.t === 'bloc'))"), [400, 600])

    # -- la derniere ligne : quatre icones, deplacer, gomme, supprimer, annuler
    essais.verifier('la derniere ligne porte quatre icones',
                    banc.js("[...document.querySelectorAll('#dactions .dact')].map(b => b.getAttribute('aria-label'))"),
                    ['Déplacer', 'Gomme', 'Supprimer', 'Annuler'])
    essais.verifier('elle est sous la barre des couleurs',
                    banc.js("$('dactions').getBoundingClientRect().top >= $('doutils').getBoundingClientRect().bottom - 1"), True)
    r = banc.js("""(() => { const o = dessin.objets.find(x => x.t === 'cam'), n = dessin.objets.length; dessin.selection = o;
      document.querySelector('#dactions .dact[aria-label=Supprimer]').click();
      const apres = [dessin.objets.length === n - 1, dessin.objets.includes(o)];
      annulerTrait(); return apres.concat([dessin.objets.some(x => x.n === o.n)]); })()""")
    essais.verifier('la corbeille retire l objet saisi, Annuler le rend', r, [True, False, True])
    banc.js("document.querySelector('#dactions .dact[aria-label=Gomme]').click()")
    essais.verifier('l icone de la gomme s allume', banc.js("[dessin.outil, document.querySelector('#dactions .dact[aria-label=Gomme]').classList.contains('on')]"), ['gomme', True])

    essais.exceptions(banc)
essais.bilan()
