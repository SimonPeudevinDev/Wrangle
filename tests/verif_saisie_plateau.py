# -*- coding: utf-8 -*-
"""Ce qui fait gagner du temps sur le plateau.

- La prise suivante reprend la focale de la prise d'avant telle quelle : le
  depart seul, ou le depart et l'arrivee apres un zoom.
- La carte, a cote du clip, se lit dans son nom ARRI (A_0001C0004 -> A_0001) ;
  un identifiant tape a la main (1F6K) n'est pas ecrase.
- Cadrage et mouvement se choisissent a plusieurs (« Poitrine / Americain »).
- Seul le plan que le Moteur vise deplie ses prises ; les autres les replient
  en une ligne, qu'un appui deplie."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

essais = Essais(largeur=64)
with Banc(8784, 9384, taille=(420, 900)) as banc:
    banc.vue(390, 844)
    banc.ouvrir()
    banc.nommer()                                    # Simon

    # -- la focale d'avant, telle quelle
    banc.js("""
      window.p0 = DB.plans[0]; window.p1 = DB.plans[1];
      window.t1 = ajouterPrise(p0.id); patch('prise', t1.id, { focale: '20 mm', focaleStop: '35 mm' });
      window.t2 = ajouterPrise(p0.id);
    """)
    essais.verifier('apres un zoom, la prise suivante reprend depart et arrivee', banc.js("[t2.focale, t2.focaleStop]"), ['20 mm', '35 mm'])
    banc.js("patch('prise', t2.id, { focale: '50 mm', focaleStop: '' }); window.t3 = ajouterPrise(p0.id)")
    essais.verifier('sans zoom, le depart seul', banc.js("[t3.focale, t3.focaleStop]"), ['50 mm', ''])

    # -- la carte, lue dans le clip
    essais.verifier('la carte d un nom de clip ARRI',
                    banc.js("['A_0001C0004', 'A001C003', 'A_0001C007_260921_095621_a1F6K', 'SCENE12', ''].map(carteDuClip)"),
                    ['A_0001', 'A001', 'A_0001', '', ''])
    banc.js("openPrise(t3.id)")
    essais.verifier('la carte est a cote du clip, plus dans Fichier & camera',
                    [banc.js("!!document.querySelector('#sbody .clip-duo #carte-in')"), banc.js("document.querySelectorAll('#sbody [data-k=\"carte\"]').length")], [True, 1])
    banc.js("(() => { const i = $('clip-in'); i.value = 'B_0002C0011'; live(i); })()")
    essais.verifier('taper le clip remplit la carte', [banc.js("t3.carte"), banc.js("$('carte-in').value")], ['B_0002', 'B_0002'])
    banc.js("(() => { const c = $('carte-in'); c.value = '1F6K'; live(c); const i = $('clip-in'); i.value = 'B_0002C0012'; live(i); })()")
    essais.verifier('une carte tapee a la main (1F6K) reste', banc.js("t3.carte"), '1F6K')
    # le +1 part du dernier clip note sur une autre prise : B_0002C0012 -> B_0002C0013
    banc.js("patch('prise', t2.id, { clip: 'B_0002C0012' }); patch('prise', t3.id, { carte: 'A_0009' }); appliquerClip(t3.id)")
    essais.verifier('le +1 du clip suit, la carte avec', [banc.js("t3.clip"), banc.js("t3.carte")], ['B_0002C0013', 'B_0002'])
    banc.js("closeSheet()")

    # -- cadrage et mouvement a plusieurs
    banc.js("patch('plan', p0.id, { cadrage: '', mouv: '' }); openPlan(p0.id); ouvrirChamp('cadrage')")
    essais.verifier('les tuiles du cadrage : des cadrages simples, pas de combinaisons',
                    banc.js("[...document.querySelectorAll('.champ[data-champ=\"cadrage\"] .tuile[data-f]')].some(b => b.dataset.f.indexOf(' / ') >= 0)"), False)
    banc.js("choisirChamp('cadrage', 'Poitrine'); choisirChamp('cadrage', 'Américain')")
    essais.verifier('deux cadrages, et la ligne reste ouverte', [banc.js("plan(p0.id).cadrage"), banc.js("champOuvert")], ['Poitrine / Américain', 'cadrage'])
    essais.verifier('les deux tuiles sont allumees',
                    banc.js("[...document.querySelectorAll('.champ[data-champ=\"cadrage\"] .tuile.on')].map(b => b.dataset.f)"), ['Poitrine', 'Américain'])
    banc.js("choisirChamp('cadrage', 'Poitrine')")
    essais.verifier('un second appui retire le cadrage', banc.js("plan(p0.id).cadrage"), 'Américain')
    banc.js("ouvrirChamp('mouv'); choisirChamp('mouv', 'Pan'); choisirChamp('mouv', 'Tilt')")
    essais.verifier('le mouvement aussi', banc.js("plan(p0.id).mouv"), 'Pan / Tilt')
    banc.js("closeSheet()")

    # -- les prises replieees : seul le plan vise deplie les siennes
    banc.js("ajouterPrise(p1.id); viser(p0.id, true); renderList()"); time.sleep(0.3)
    deplie = lambda pid: banc.js("(() => { const b = document.querySelector('#l-shoot .plan[data-id=\"' + %s + '\"]'); return [b.querySelectorAll('.prise').length > 0, !!b.querySelector('.prises-repliees')]; })()" % pid)
    essais.verifier('le plan vise deplie ses prises', deplie('p0.id'), [True, False])
    essais.verifier('l autre les replie en une ligne', deplie('p1.id'), [False, True])
    essais.verifier('la ligne dit combien', banc.js("document.querySelector('#l-shoot .plan[data-id=\"' + p1.id + '\"] .prises-repliees').textContent.trim()"), '1 prise')
    banc.js("document.querySelector('#l-shoot .plan[data-id=\"' + p1.id + '\"] .prises-repliees').click()"); time.sleep(0.3)
    essais.verifier('un appui la deplie et vise ce plan', [deplie('p1.id'), banc.js("planVise().id === p1.id")], [[True, False], True])
    essais.verifier('l autre se replie', deplie('p0.id'), [False, True])
    banc.js("document.querySelector('#l-shoot .plan[data-id=\"' + p0.id + '\"] .viser').click()"); time.sleep(0.3)
    essais.verifier('l anneau du Moteur fait de meme', [deplie('p0.id'), deplie('p1.id')], [[True, False], [False, True]])

    # -- les sequences sur deux chiffres, les cinq jours du tournage
    banc.js("patch('plan', p1.id, { seq: '3' })")
    essais.verifier('le menu des sequences : deux chiffres, dans l ordre',
                    banc.js("(() => { const l = LISTES['dl-seq'](); return [l.indexOf('3'), l.indexOf('03') >= 0, l.slice().sort((a, b) => parseInt(a, 10) - parseInt(b, 10)).join() === l.join()]; })()"),
                    [-1, True, True])
    banc.js("openPlan(p1.id)"); time.sleep(0.2)
    banc.js("(() => { const i = document.querySelector('#sbody input[data-k=\"seq\"]'); i.value = '4'; i.dispatchEvent(new Event('change')); })()")
    essais.verifier('une sequence tapee « 4 » devient « 04 » en quittant le champ', banc.js("plan(p1.id).seq"), '04')
    banc.js("closeSheet()"); time.sleep(0.6)
    essais.verifier('le menu des jours : J1 a J5, sans J6, J7 ni CG', banc.js("LISTES['dl-jour']()"), ['J1', 'J2', 'J3', 'J4', 'J5'])

    # -- la preparation est a Simon
    essais.verifier('Simon voit la preparation', banc.js("document.querySelector('nav button[data-v=\"prep\"]').hidden"), False)
    banc.js("document.querySelector('nav button[data-v=\"prep\"]').click(); changerDePersonne('Romain')"); time.sleep(0.4)
    essais.verifier('Romain ne la voit pas, et revient au tournage', [banc.js("document.querySelector('nav button[data-v=\"prep\"]').hidden"), banc.js("view")], [True, 'shoot'])
    banc.js("document.querySelector('nav button[data-v=\"prep\"]').click()")
    essais.verifier('et ne peut pas y aller', banc.js("view"), 'shoot')
    banc.js("changerDePersonne('Simon')"); time.sleep(0.4)
    essais.verifier('Simon la retrouve', banc.js("document.querySelector('nav button[data-v=\"prep\"]').hidden"), False)

    # -- le bouton Retour du navigateur ferme la fiche, il ne quitte pas le site
    etat = lambda: banc.js("[openType, openType === 'plan' ? plan(openId).plan : openType === 'prise' ? prise(openId).n : null, $('sheet').classList.contains('on')]")
    retour = lambda: (banc.js("history.back()"), time.sleep(0.6))
    banc.js("openPlan(p0.id)"); time.sleep(0.3)
    banc.js("openPrise(t1.id)"); time.sleep(0.3)
    retour()
    essais.verifier('Retour depuis une prise ouverte depuis son plan : le plan', etat(), ['plan', banc.js("p0.plan"), True])
    retour()
    essais.verifier('Retour encore : la fiche se ferme, on reste sur le site', [etat(), banc.js("location.pathname"), banc.js("typeof DB")], [[None, None, False], '/', 'object'])
    banc.js("openPrise(t1.id)"); time.sleep(0.2)
    banc.js("openPrise(t2.id)"); time.sleep(0.2)
    banc.js("openPrise(t3.id)"); time.sleep(0.2)
    retour()
    essais.verifier('d une prise a la suivante, aux fleches : un seul Retour ferme', etat(), [None, None, False])
    banc.js("openPlan(p1.id)"); time.sleep(0.3)
    banc.js("closeSheet()"); time.sleep(0.6)
    essais.verifier('fermee a la main : ses marques quittent l historique', [etat()[0], banc.js("!!(history.state && history.state.fiche)")], [None, False])
    essais.exceptions(banc)
essais.bilan()
