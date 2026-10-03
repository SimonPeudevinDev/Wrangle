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

    # un point de la feuille, la ou l'ecran le montre : le dessin et le doigt doivent s'accorder
    juste = banc.js("(q => pointCroquis({ clientX: q[0], clientY: q[1] }))(ecranDe([300, 200]))")
    essais.verifier('sous la feuille de travers, le doigt touche le bon point', all(abs(v - w) <= 1 for v, w in zip(juste, [300, 200])), True)
    essais.verifier('le canevas garde la taille de la zone, meme zoome (pas de bandes noires)',
                    banc.js("(c => c.clientWidth === $('dzone').clientWidth && c.width <= c.clientWidth * (devicePixelRatio || 1) + 1)($('croquis'))"), True)

    # en diagonale, la vue entiere ne bascule pas : le zoom reste le meme
    r = banc.js("""(() => { const k0 = vueCroquis().k, ks = [];
      for (const d of [30, 44, 46, 60, 89]){ geste([[0, 100], [d, 100]]); ks.push(vueCroquis().k / k0); }
      return ks.map(x => Math.round(x * 1000) / 1000); })()""")
    essais.verifier('tourner en diagonale ne zoome pas', r, [1, 1, 1, 1, 1])
    banc.js("dessin.rot = 28; tailleCroquis()")

    r = banc.js("geste([[20, 100], [50, 100], [72, 100]])")
    essais.verifier('a 2 degres de 90 : pas d aimant, la feuille reste a 88', round(r['rot']), 88)
    r = banc.js("geste([[-20, 100], [-60, 100], [-98, 100]])")
    essais.verifier('ramenee a 2 degres de l origine : la feuille se recolle a 0', r['rot'], 0)
    essais.verifier('reposee droite : l appareil garde 0', banc.js('UI.rotCroquis'), 0)

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

    # -- la derniere ligne : trois icones, deplacer, gomme, annuler ; la corbeille en haut a droite
    essais.verifier('la derniere ligne porte trois icones',
                    banc.js("[...document.querySelectorAll('#dactions .dact')].map(b => b.getAttribute('aria-label'))"),
                    ['Déplacer', 'Gomme', 'Annuler'])
    essais.verifier('elle est sous la barre des couleurs',
                    banc.js("$('dactions').getBoundingClientRect().top >= $('doutils').getBoundingClientRect().bottom - 1"), True)
    essais.verifier('la corbeille est le dernier bouton de l en-tete, a droite',
                    banc.js("(t => t.lastElementChild.lastElementChild.id === 'dsuppr' && !!$('dsuppr').querySelector('svg'))(document.querySelector('#voile-dessin .dtete'))"), True)
    essais.verifier('plus de bandeau dans l en-tete', banc.js("!!document.getElementById('croq-deja')"), False)
    r = banc.js("""(() => { const o = dessin.objets.find(x => x.t === 'cam'), n = dessin.objets.length; dessin.selection = o;
      $('dsuppr').click();
      const apres = [dessin.objets.length === n - 1, dessin.objets.includes(o)];
      annulerTrait(); return apres.concat([dessin.objets.some(x => x.n === o.n)]); })()""")
    essais.verifier('la corbeille retire l objet saisi, Annuler le rend', r, [True, False, True])
    banc.js("document.querySelector('#dactions .dact[aria-label=Gomme]').click()")
    essais.verifier('l icone de la gomme s allume', banc.js("[dessin.outil, document.querySelector('#dactions .dact[aria-label=Gomme]').classList.contains('on')]"), ['gomme', True])

    # -- quelqu'un d'autre ouvre ce schema : une fenetre le dit, une seule fois
    banc.js("RESEAU.presence.push({ client:'autre-appareil', nom:'Simon', actif:'croquis:' + dessin.planId }); majDejaCroquis()")
    essais.verifier('une fenetre : Simon modifie deja ce schema',
                    [banc.js("$('dlg').hidden"), banc.js("$('dlg-titre').textContent")], [False, 'Simon modifie déjà ce schéma'])
    banc.js("$('dlg-oui').click(); majDejaCroquis()")
    essais.verifier('lue, elle ne revient pas', banc.js("$('dlg').hidden"), True)

    essais.exceptions(banc)
essais.bilan()
