# -*- coding: utf-8 -*-
"""Le croquis : dessine, enregistre, puis redessine a l'ouverture de la fiche.

Le projet ne garde que les traits. L'apercu de la fiche n'est plus une image
enregistree : il se refait depuis ces traits, ce qui divise par quinze le poids
d'un croquis et supprime la copie du plan du decor dans chaque plan.

  py tests/verif_croquis.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais()
with Banc(8786, 9371) as banc:
    banc.ouvrir()
    banc.nommer()

    # -- un decor fourni avec la page (public/maps) : son plan sert de fond, sans rien peser dans le projet
    banc.js("patch('plan', DB.plans[0].id, { lieu: 'Atelier', fondLieu: '' })")
    essais.verifier('le plan de l Atelier est fourni, hors du projet',
                    [banc.js("fondDecor('Atelier')"), banc.js("!!(DB.prod.fonds || {}).Atelier")], ['public/maps/atelier.webp', False])
    banc.js('openPlan(DB.plans[0].id)'); time.sleep(0.8)
    essais.verifier('son plan s affiche sous le croquis, sans corbeille (il ne se retire pas)',
                    [banc.js("!!document.getElementById('croq-apercu')"), banc.js("!!document.querySelector('.croq-outils .d')")], [True, False])
    banc.js('closeSheet()'); time.sleep(0.3)

    # -- un plan sans croquis, dans un decor sans plan, propose de dessiner
    banc.js("patch('plan', DB.plans[0].id, { lieu: 'Décor de test' })")
    banc.js('openPlan(DB.plans[0].id)'); time.sleep(0.6)
    essais.verifier('plan vierge : le bouton « Dessiner le set »',
                    banc.js("!!document.querySelector('.croq-cadre.vide .croq-vide')"), True)
    essais.verifier('plan vierge : pas de canvas d apercu',
                    banc.js("!!document.getElementById('croq-apercu')"), False)

    # -- on dessine trois traits dans l'editeur, puis on enregistre
    banc.js('ouvrirCroquis(DB.plans[0].id)'); time.sleep(0.8)
    banc.js("""
      dessin.traits.push({ c:'#e02020', w:3, n:1,
        pts:[[200,200],[400,260],[520,180],[640,300]] });
      dessin.traits.push({ c:'#1060d0', w:3, n:2,
        pts:[[300,500],[500,540],[700,460]] });
      dessin.traits.push({ c:'#18a558', w:2, n:3,
        pts:[[250,700],[450,760],[650,700],[850,780]] });
      enregistrerCroquis();
    """)
    time.sleep(0.8)

    garde = banc.js("""
      (() => { const p = DB.plans[0];
        return { traits: (p.croquis && p.croquis.traits || []).length,
                 raster: 'croquisImg' in p,
                 poids: Math.round(JSON.stringify(p).length / 1024 * 10) / 10 }; })()
    """)
    essais.verifier('les trois traits sont dans le projet', garde['traits'], 3)
    essais.verifier('aucune image n est enregistree', garde['raster'], False)
    essais.detail('le plan entier, croquis compris : %s Ko' % garde['poids'])

    # -- la fiche rouverte redessine l'apercu
    banc.js('fermerCroquis(); openPlan(DB.plans[0].id)'); time.sleep(1.0)
    essais.verifier('la fiche montre un canvas d apercu',
                    banc.js("!!document.getElementById('croq-apercu')"), True)
    dessine = banc.js("""
      (() => {
        const cv = document.getElementById('croq-apercu');
        if (!cv || !cv.width) return 'pas de canvas';
        const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
        let couleurs = 0;
        for (let i = 0; i < d.length; i += 4)
          if (d[i+3] > 10 && (Math.abs(d[i] - d[i+1]) > 30 || Math.abs(d[i+1] - d[i+2]) > 30)) couleurs++;
        return couleurs;
      })()
    """)
    essais.verifier('l apercu porte bien des traits de couleur', isinstance(dessine, int) and dessine > 500, True)
    essais.detail('%r pixels colores dans l apercu' % dessine)

    # -- plusieurs croquis : « + Croquis » en ouvre un neuf, qui n'existe qu'enregistre
    essais.verifier('un croquis dessine propose « + Croquis »',
                    banc.js("[...document.querySelectorAll('.croq-onglets button')].map(b => b.textContent.trim())"), ['+ Croquis'])
    banc.js("nouveauCroquis(DB.plans[0].id)"); time.sleep(0.8)
    essais.verifier('le nouveau croquis s ouvre vide, numero 2',
                    banc.js("[dessin.index, dessin.traits.length, document.querySelector('#voile-dessin .dtitre b').textContent]"),
                    [1, 0, 'Croquis 2 · shot ' + banc.js("DB.plans[0].plan")])
    banc.js("dessin.traits.push({ c:'#4f8fd6', w:3, n:1, pts:[[100,100],[900,700]] }); enregistrerCroquis(); fermerCroquis()"); time.sleep(0.6)
    essais.verifier('enregistre, il rejoint le plan sans toucher au premier',
                    banc.js("[(DB.plans[0].croquisPlus || []).length, DB.plans[0].croquis.traits.length]"), [1, 3])
    essais.verifier('la fiche a un onglet par croquis, le second montre',
                    banc.js("[...document.querySelectorAll('.croq-onglets button')].map(b => b.textContent.trim() + (b.classList.contains('on') ? '*' : ''))"),
                    ['Croquis 1', 'Croquis 2*', '+ Croquis', 'Supprimer le croquis 2'])
    banc.js("voirCroquis(DB.plans[0].id, 0)"); time.sleep(0.4)
    essais.verifier('l onglet 1 rouvre le premier', banc.js("croquisVu(DB.plans[0])"), 0)
    banc.js("supprimerCroquis(DB.plans[0].id)"); time.sleep(0.3); banc.js("fermerDialogue(true)"); time.sleep(0.4)
    essais.verifier('supprimer le premier : le second prend sa place',
                    banc.js("[DB.plans[0].croquis.traits.length, (DB.plans[0].croquisPlus || []).length]"), [1, 0])

    # -- un vieux projet qui portait une image la perd au chargement
    banc.js("""
      DB.plans[1].croquisImg = 'data:image/jpeg;base64,AAAA';
      DB = normaliser(DB);
    """)
    essais.verifier('un ancien apercu enregistre est jete au chargement',
                    banc.js("'croquisImg' in DB.plans[1]"), False)

    # -- les photos importees : le format le plus leger des deux, jamais pire
    essais.verifier('le navigateur sait ecrire du WebP', banc.js('SAIT_WEBP'), True)
    choix = banc.js("""
      (() => {
        const c = document.createElement('canvas'); c.width = 900; c.height = 600;
        const g = c.getContext('2d');
        g.fillStyle = '#fff'; g.fillRect(0, 0, 900, 600);          // un plan de decor au trait
        g.strokeStyle = '#222'; g.lineWidth = 3;
        for (let i = 0; i < 14; i++) g.strokeRect(40 + i * 28, 40 + i * 18, 200, 140);
        const j = c.toDataURL('image/jpeg', .72).length, w = c.toDataURL('image/webp', .72).length;
        return [Math.round(j / 1024), Math.round(w / 1024), Math.min(j, w) <= j];
      })()
    """)
    essais.verifier('sur un plan au trait, on ne garde jamais le plus lourd', choix[2], True)
    essais.detail('au trait : JPEG %d Ko, WebP %d Ko' % (choix[0], choix[1]))

    # -- l'aimant : un mur presque droit se couche a l'horizontale ; un second mur
    #    commence au bout du premier ; avec Alt, a main levee
    banc.js('ouvrirCroquis(DB.plans[2].id)'); time.sleep(0.8)
    # la feuille a l'ecran : le canevas remplit la zone et la dessine, droite, en vue entiere
    r = banc.js("(() => { const a = ecranDe([0, 0]), b = ecranDe([dessin.w, dessin.h]); return [a[0], a[1], b[0] - a[0], b[1] - a[1]]; })()")
    ecran = lambda fx, fy: (r[0] + r[2] * fx, r[1] + r[3] * fy)

    def tirer(de, a, alt=False):
        mods = 1 if alt else 0
        x, y = ecran(*de)
        banc.cdp.appel('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', buttons=1, clickCount=1, modifiers=mods)
        for k in range(1, 6):
            xx, yy = ecran(de[0] + (a[0] - de[0]) * k / 5, de[1] + (a[1] - de[1]) * k / 5)
            banc.cdp.appel('Input.dispatchMouseEvent', type='mouseMoved', x=xx, y=yy, button='left', buttons=1, modifiers=mods)
        x, y = ecran(*a)
        banc.cdp.appel('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', buttons=0, clickCount=1, modifiers=mods)
        time.sleep(0.2)

    banc.js("outilCroquis('objet', 'mur')")
    tirer((0.20, 0.30), (0.60, 0.33))        # a 4 ou 5° de l'horizontale
    m1 = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.t, o.y1, o.y2, o.x2]; })()")
    essais.verifier('aimant : le mur presque droit se couche a l horizontale', [m1[0], m1[1] == m1[2]], ['mur', True])
    tirer((0.601, 0.305), (0.605, 0.70))     # commence tout pres du bout du premier, descend presque droit
    m2 = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.x1, o.y1, o.x2]; })()")
    essais.verifier('aimant : le second mur part du bout du premier, et descend a la verticale', [m2[0] == m1[3], m2[1] == m1[2], m2[0] == m2[2]], [True, True, True])
    tirer((0.20, 0.60), (0.40, 0.63), alt=True)
    m3 = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return o.y1 !== o.y2; })()")
    essais.verifier('avec Alt, a main levee', m3, True)

    # -- la fleche se courbe par son point du milieu, et se redresse en y revenant
    banc.js("outilCroquis('objet', 'fleche')")
    tirer((0.20, 0.85), (0.60, 0.85))
    banc.js("outilCroquis('move'); dessin.selection = dessin.objets[dessin.objets.length - 1]; rendreCroquis()")
    tirer((0.40, 0.85), (0.40, 0.72))
    f = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.t, o.mx != null, o.my < o.y1]; })()")
    essais.verifier('la fleche tiree par son milieu se courbe', f, ['fleche', True, True])
    essais.verifier('la fleche courbe se saisit sur sa courbe',
                    banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return touche([o.mx, o.my], o); })()"), True)
    tirer((0.40, 0.72), (0.402, 0.852))
    essais.verifier('ramenee sur la droite, elle se redresse',
                    banc.js("dessin.objets[dessin.objets.length - 1].mx == null"), True)

    # -- la fleche libre : un trajet dessine a la main, en arc ; trop court, il n'est pas garde
    def tracer(points):
        x, y = ecran(*points[0])
        banc.cdp.appel('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', buttons=1, clickCount=1)
        for q in points[1:]:
            x, y = ecran(*q)
            banc.cdp.appel('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y, button='left', buttons=1)
        banc.cdp.appel('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', buttons=0, clickCount=1)
        time.sleep(0.2)
    import math
    avant, traits = banc.js("[dessin.objets.length, dessin.traits.length]")
    banc.js("outilCroquis('objet', 'trajet')")
    tracer([(0.30 + 0.2 * math.cos(math.pi * k / 30), 0.55 - 0.2 * math.sin(math.pi * k / 30)) for k in range(31)])
    tj = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.t, o.pts.length, dessin.traits.length]; })()")
    essais.verifier('la fleche libre garde son trajet, simplifie, sans laisser de trait', [tj[0], 3 <= tj[1] <= 30, tj[2]], ['trajet', True, traits])
    essais.verifier('elle se saisit sur son trajet',
                    banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return touche(o.pts[Math.floor(o.pts.length / 2)], o); })()"), True)
    tracer([(0.5, 0.5), (0.505, 0.5)])
    essais.verifier('un trajet trop court n est pas pose', banc.js("dessin.objets.length"), avant + 1)

    # -- le lissage : un trait tremble au crayon en sort plus calme, et finit sous la main
    banc.js("outilCroquis('couleur', '#1c1410'); dessin.outil = 'crayon'; UI.lissage = true; majOutils()")
    tracer([(0.10 + 0.4 * k / 40, 0.45 + (0.012 if k % 2 else -0.012)) for k in range(41)])
    li = banc.js("""(() => { const p = dessin.traits[dessin.traits.length - 1].pts;
      const ys = p.slice(5, -5).map(q => q[1]); return [Math.max(...ys) - Math.min(...ys), p[p.length - 1][0]]; })()""")
    brut = banc.js("0.024 * dessin.h")
    essais.verifier('le lissage calme le tremblement de moitie au moins', li[0] < brut / 2, True)
    essais.detail('ecart vertical : %.1f lisse, %.1f a la main' % (li[0], brut))
    essais.verifier('et le trait finit ou la main s est levee', abs(li[1] - banc.js("0.5 * dessin.w")) < 3, True)
    essais.verifier('le bouton Lissage est allume', banc.js("[...document.querySelectorAll('#doutils .btn')].some(b => b.textContent === 'Lissage' && b.classList.contains('p'))"), True)

    # -- une couleur au choix
    banc.js("document.querySelector('#doutils .dperso').click()"); time.sleep(0.2)
    essais.verifier('la pastille arc-en-ciel ouvre le selecteur de la charte', banc.js("!$('dpick').hidden"), True)
    banc.js("hexPick('#8844cc'); fermerPick()"); time.sleep(0.2)
    essais.verifier('la couleur au choix devient celle du crayon, et sa pastille la prend',
                    banc.js("[dessin.couleur, document.querySelector('#doutils .dperso').classList.contains('on')]"), ['#8844cc', True])
    essais.verifier('et rejoint les couleurs recentes', banc.js("UI.couleurs[0]"), '#8844cc')

    # -- le soleil se pose et s'oriente comme une lumiere
    banc.js("outilCroquis('objet', 'soleil')")
    tirer((0.80, 0.20), (0.70, 0.35))
    s = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.t, o.a > 0]; })()")
    essais.verifier('le soleil se pose, tourne vers ou va sa lumiere', s, ['soleil', True])

    # -- la point light prend la couleur choisie ; saisie, une autre pastille la recolore (et Annuler revient)
    banc.js("outilCroquis('couleur', '#4f8fd6'); outilCroquis('objet', 'ponct')")
    tirer((0.30, 0.70), (0.30, 0.70))
    s = banc.js("(() => { const o = dessin.objets[dessin.objets.length - 1]; return [o.t, o.c]; })()")
    essais.verifier('la point light se pose dans la couleur choisie', s, ['ponct', '#4f8fd6'])
    banc.js("outilCroquis('move')")
    tirer((0.30, 0.70), (0.30, 0.70))
    banc.js("outilCroquis('couleur', '#e8675e')")
    essais.verifier('saisie, elle prend la pastille touchee', banc.js("dessin.selection && dessin.selection.c"), '#e8675e')
    banc.js("annulerTrait()")
    essais.verifier('Annuler lui rend sa couleur', banc.js("dessin.objets[dessin.objets.length - 1].c"), '#4f8fd6')

    # -- les volets du projecteur : le losange ouvre ou referme le faisceau, au degre pres
    banc.js("outilCroquis('objet', 'lum')")
    tirer((0.50, 0.50), (0.60, 0.50))
    banc.js("outilCroquis('move')")
    tirer((0.50, 0.50), (0.50, 0.50))
    vol = banc.js("(() => { const p = poigneesDe(dessin.selection).find(q => q.volet); return p && ecranDe([p.x, p.y]); })()")
    essais.verifier('le projecteur saisi a sa poignee de volets', bool(vol), True)
    o = banc.js("(() => { const o = dessin.selection; return ecranDe([o.x, o.y]); })()")
    # tirer le losange vers l'axe du faisceau le referme
    x0, y0 = vol
    banc.cdp.appel('Input.dispatchMouseEvent', type='mousePressed', x=x0, y=y0, button='left', buttons=1, clickCount=1)
    for k in range(1, 6):
        banc.cdp.appel('Input.dispatchMouseEvent', type='mouseMoved', x=x0, y=y0 + (o[1] - y0) * k / 6, button='left', buttons=1)
    banc.cdp.appel('Input.dispatchMouseEvent', type='mouseReleased', x=x0, y=y0 + (o[1] - y0) * 5 / 6, button='left', buttons=0, clickCount=1)
    time.sleep(0.2)
    bd = banc.js("(() => { const b = dessin.selection.bd; return [b != null && b < VOLET_DEF, b >= VOLET_MIN, Math.abs(b * 180 / Math.PI - Math.round(b * 180 / Math.PI)) < 1e-6]; })()")
    essais.verifier('tirer le losange vers l axe referme les volets, au degre pres', bd, [True, True, True])
    banc.js("fermerCroquis()")

    essais.exceptions(banc)
essais.bilan()
