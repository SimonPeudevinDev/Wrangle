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

    # -- un plan sans croquis propose de dessiner
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

    essais.exceptions(banc)
essais.bilan()
