# -*- coding: utf-8 -*-
"""La rangee des jours sur telephone : trois jours, l'actif au milieu.

Un tournage de huit jours ne tient pas dans la largeur d'un pouce. Plutot que
de laisser defiler une rangee de neuf onglets, chacun prend le tiers de la
rangee et l'actif se cale au centre : on a toujours la veille, le jour et le
lendemain sous les yeux, et une fleche fait glisser d'un jour.

  py tests/verif_barre_jours.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

VISIBLES = """
  (() => {
    const row = document.getElementById('c-jour');
    const r = row.getBoundingClientRect();
    return [...row.querySelectorAll('.chip')].filter(c => {
      const b = c.getBoundingClientRect();
      return b.left >= r.left - 2 && b.right <= r.right + 2;
    }).map(c => c.textContent.trim() + (c.classList.contains('on') ? ' *' : ''));
  })()
"""
TIERS = """
  (() => { const row = document.getElementById('c-jour');
    const c = row.querySelector('.chip');
    return Math.abs(c.getBoundingClientRect().width - row.clientWidth / 3); })()
"""

essais = Essais(largeur=44)
with Banc(8795, 9380, taille=(390, 844)) as banc:
    # iPhone 14 : 390 px de large, le plus etroit des telephones courants
    banc.vue(390, 844)
    banc.ouvrir()
    banc.nommer()

    jours = banc.js("joursConnus().filter(j => j)")
    essais.verifier('le decoupage a de quoi deborder la rangee', len(jours) >= 5, True)

    # un onglet vaut le tiers de la rangee, a un pixel d arrondi pres
    essais.verifier('un onglet vaut le tiers de la rangee', banc.js(TIERS) < 1.5, True)

    essais.verifier('aucun nom n est coupe', banc.js(
        "[...document.querySelectorAll('#c-jour .chip')]"
        ".filter(c => c.scrollWidth > c.clientWidth + 1).map(c => c.textContent.trim())"), [])

    # au milieu du tournage : la veille, le jour, le lendemain
    banc.js("setJour('%s')" % jours[len(jours) // 2]); time.sleep(0.5)
    vus = banc.js(VISIBLES)
    essais.verifier('trois jours a l ecran, pas un de plus', len(vus), 3)
    essais.verifier('l actif est celui du milieu', vus[1].endswith(' *'), True)

    # au debut : la rangee bute, l actif reste visible
    banc.js("setJour('*')"); time.sleep(0.5)
    vus = banc.js(VISIBLES)
    essais.verifier('au debut, trois jours encore', len(vus), 3)
    essais.verifier('au debut, l actif est le premier', vus[0].endswith(' *'), True)
    essais.verifier('la fleche precedente est eteinte',
                    banc.js("document.querySelector('#v-shoot .jours .fleche').disabled"), True)

    # a la fin : idem de l autre cote
    banc.js('setJour(ordreJours()[ordreJours().length - 1])'); time.sleep(0.5)
    vus = banc.js(VISIBLES)
    essais.verifier('a la fin, trois jours encore', len(vus), 3)
    essais.verifier('a la fin, l actif est le dernier', vus[2].endswith(' *'), True)

    # la fleche fait avancer d un seul jour
    banc.js("setJour('%s')" % jours[0]); time.sleep(0.4)
    banc.js("jourVoisin(1, 'shoot')"); time.sleep(0.5)
    essais.verifier('une fleche avance d un jour', banc.js('fJour'), jours[1])

    # sur grand ecran la rangee reprend sa forme libre
    banc.vue(1280, 900, mobile=False, echelle=1)
    banc.js('renderShoot()'); time.sleep(0.4)
    essais.verifier('sur grand ecran, les onglets ne font plus un tiers', banc.js("""
      (() => { const row = document.getElementById('c-jour');
        const c = row.querySelector('.chip');
        return c.getBoundingClientRect().width < row.clientWidth / 4; })()
    """), True)

    essais.exceptions(banc)
essais.bilan()
