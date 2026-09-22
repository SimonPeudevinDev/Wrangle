# -*- coding: utf-8 -*-
"""Recharger la page ramene la ou on etait.

Sur le plateau on recharge pour prendre une mise a jour ; on doit retrouver
l'onglet, la fiche ouverte, la ligne ouverte dedans et le defilement. Un
nouvel onglet, lui, part propre.

  py tests/verif_reprise.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

# « La meme place », c'est le meme contenu sous les yeux, pas le meme chiffre :
# quand une image se charge plus haut, le navigateur decale le defilement pour
# garder ce qu'on regardait en place (ancrage). On repere donc la premiere
# ligne visible de la fiche et le premier plan visible de la liste, avec leur
# position a l'ecran, et on les compare a une vingtaine de pixels pres.
REPERE = """
  (() => {
    const sb = document.getElementById('sbody'), r = sb.getBoundingClientRect();
    const c = [...sb.querySelectorAll('.champ[data-champ]')].find(e => e.getBoundingClientRect().bottom > r.top + 1);
    const p = [...document.querySelectorAll('#l-shoot .plan[data-id]')].find(e => e.getBoundingClientRect().bottom > 160);
    return { fiche: c ? [c.dataset.champ, Math.round(c.getBoundingClientRect().top - r.top)] : null,
             liste: p ? [p.dataset.id, Math.round(p.getBoundingClientRect().top)] : null };
  })()
"""
ETAT = "[openType, openId, champOuvert, Math.round(window.scrollY), document.getElementById('sbody').scrollTop]"


# Apres rechargement, on cherche ce meme plan par son identifiant : la carte qui
# passe la barre des 160 px peut changer pour quelques pixels de derive, sans
# que ce qu'on regardait ait bouge.
POSITION = """
  (id => { const e = document.querySelector('#l-shoot .plan[data-id="' + id + '"]');
           return e ? Math.round(e.getBoundingClientRect().top) : null; })(%s)
"""


def meme(a, b):
    return bool(a and b and a[0] == b[0] and abs(a[1] - b[1]) <= 24)


essais = Essais(largeur=50)
with Banc(8798, 9383, taille=(430, 932)) as banc:
    banc.ouvrir()
    banc.nommer()

    # -- on descend dans la liste, on ouvre un plan, on descend dans sa fiche, on ouvre une ligne
    banc.js("setJour('*'); window.scrollTo(0, 900)"); time.sleep(0.4)
    cible_id = banc.js('DB.plans[6].id')
    banc.js('openPlan(%s)' % json.dumps(cible_id)); time.sleep(0.5)
    banc.js("ouvrirChamp('cadrage')"); time.sleep(0.3)
    banc.js("document.getElementById('sbody').scrollTop = 400"); time.sleep(0.4)
    avant = banc.js(ETAT)
    essais.verifier('etat de depart note', avant[0], 'plan')
    note = banc.js("JSON.parse(sessionStorage.getItem('fstdw.place') || 'null')")
    essais.verifier('la place est notee dans la session', note and note.get('openId') == cible_id, True)
    rep_avant = banc.js(REPERE)

    # -- rechargement : tout doit etre retrouve
    # on laisse du temps : les images de la fiche se chargent, elle grandit, le defilement se remet
    banc.ouvrir(repos=2.7)
    apres = banc.js(ETAT)
    rep_apres = banc.js(REPERE)
    essais.verifier('la fiche du meme plan est rouverte', apres[:2], ['plan', cible_id])
    essais.verifier('la ligne ouverte est la meme', apres[2], 'cadrage')
    essais.detail('fiche : defilement %d -> %d, repere %r -> %r'
                  % (avant[4], apres[4], rep_avant['fiche'], rep_apres['fiche']))
    essais.verifier('la fiche montre la meme ligne au meme endroit', meme(rep_avant['fiche'], rep_apres['fiche']), True)
    y_liste = banc.js(POSITION % json.dumps(rep_avant['liste'][0])) if rep_avant['liste'] else None
    essais.detail('liste : defilement %d -> %d, plan %r a %r -> %r'
                  % (avant[3], apres[3], rep_avant['liste'][0], rep_avant['liste'][1], y_liste))
    essais.verifier('la liste derriere montre le meme plan au meme endroit',
                    y_liste is not None and abs(y_liste - rep_avant['liste'][1]) <= 24, True)

    # -- un autre onglet, puis rechargement
    banc.js("""closeSheet(); document.querySelector('nav button[data-v="report"]').click();
               setJourR(joursConnus()[1])""")
    time.sleep(0.5)
    banc.js('window.scrollTo(0, 500)'); time.sleep(0.4)
    # la page n'est pas forcement assez haute pour 500 : on compare a ce qui a ete obtenu
    jr, y_rapport = banc.js('[fJourR, Math.round(window.scrollY)]')
    banc.ouvrir(repos=2.7)   # les vignettes du rapport se chargent, la page grandit
    essais.verifier('l onglet Rapport est retrouve', banc.js('view'), 'report')
    essais.verifier('et son jour aussi', banc.js('fJourR'), jr)
    essais.verifier('aucune fiche n est rouverte a tort', banc.js('openType'), None)
    y2 = banc.js('Math.round(window.scrollY)')
    essais.verifier('le defilement du rapport est retrouve (%d -> %d)' % (y_rapport, y2),
                    abs(y2 - y_rapport) <= 2, True)

    # -- une fiche dont le plan a disparu entre-temps : on ne rouvre rien.
    #    (la place se note au moment de quitter : on fausse la variable, pas la memoire)
    banc.js("""document.querySelector('nav button[data-v="shoot"]').click();
               openPlan(DB.plans[2].id)""")
    time.sleep(0.4)
    banc.js("openId = 'disparu'")
    banc.ouvrir(repos=1.7)
    essais.verifier('un plan disparu ne rouvre pas de fiche', banc.js('openType'), None)

    essais.exceptions(banc)
essais.bilan()
