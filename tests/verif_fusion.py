# -*- coding: utf-8 -*-
"""Fusionner deux shots tournes en un seul : le B dans le A.

Simon a 1 prise sur A et 2 sur B ; Romain, 3 sur A et 2 sur B, et une
description et un element capte sur B. Simon fusionne. Le B passe en
« Abandonne », marque ; ses textes et elements rejoignent A, pour tous. Les
prises de Simon passent sur A a la suite du plus grand numero connu chez tous
(3, celui de Romain) : 4 et 5. Quand l'appareil de Romain retrouve son espace,
il deplace les siennes de la meme facon. La page est en mode « php »."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, patienter                         # noqa: E402

PORT = 8780


def api(chemin, corps=None):
    url = 'http://localhost:%d/api/%s' % (PORT, chemin)
    if corps is None:
        return json.loads(urllib.request.urlopen(url, timeout=5).read())
    req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


def prises_romain(pid):
    return sorted((t['n'], t.get('clip', '')) for t in api('etat.php?espace=romain')['db']['prises'] if t['planId'] == pid)


essais = Essais(largeur=64)
with Banc(PORT, 9370, taille=(1200, 900)) as banc:
    banc.ouvrir('/?php=1')
    banc.nommer()                                    # Simon
    patienter(lambda: banc.js("RESEAU.etat === 'ok' && RESEAU.rev >= 1 && !RESEAU.attente.length"), tours=60)
    db = api('etat.php?espace=simon')['db']
    a, b = db['plans'][0]['id'], db['plans'][1]['id']
    pr = lambda pid, n, c: {'op': 'add', 'kind': 'prise', 'data': {'id': 'r' + c, 'planId': pid, 'n': n, 'clip': c, 'par': 'Romain'}}
    api('ops.php', {'client': 'romain1', 'nom': 'Romain', 'espace': 'romain', 'ops': [
        {'op': 'remplacer', 'db': dict(db, prises=[])},
        pr(a, 1, 'RA1'), pr(a, 2, 'RA2'), pr(a, 3, 'RA3'), pr(b, 1, 'RB1'), pr(b, 2, 'RB2'),
        {'op': 'patch', 'kind': 'plan', 'id': b, 'data': {'elements@Romain': {'hdri': True}, 'vfxDesc@Romain': 'Reflet a effacer'}}]})
    # la mise en place de Romain remplace son projet, et le remplacement passe chez Simon : on l'attend
    patienter(lambda: banc.js("!!(plan(%s) || {})['vfxDesc@Romain']" % json.dumps(b)), tours=60)
    banc.js("""
      window.A = %s; window.B = %s;
      ajouterPrise(A, false, { clip:'SA1' });
      ajouterPrise(B, false, { clip:'SB1' }); ajouterPrise(B, false, { clip:'SB2' });
      patch('plan', A, { 'vfxDesc@Simon': 'Pied de micro' });
    """ % (json.dumps(a), json.dumps(b)))
    patienter(lambda: len(api('etat.php?espace=simon')['db']['prises']) == 3, tours=40)
    banc.js("majAutres(true)"); time.sleep(1.5)

    # -- le bouton, et le choix du shot
    banc.js("openPlan(A)"); time.sleep(0.3)
    essais.verifier('la fiche du plan propose la fusion', banc.js("!!document.querySelector('#sbody .btn.fusion')"), True)
    banc.js("choisirFusion(A)"); time.sleep(0.3)
    essais.verifier('le choix : les autres shots du jour, pas lui-meme',
                    [banc.js("document.querySelectorAll('#l-pick .plan.pick').length > 0"),
                     banc.js("[...document.querySelectorAll('#l-pick .phead')].some(h => h.getAttribute('onclick').indexOf(\"'\" + A + \"', '\" + A + \"'\") >= 0)")], [True, False])
    essais.verifier('la suite commence apres le plus grand numero chez tous (Romain : 3)', banc.js("maxPrisesPartout(plan(A))"), 3)

    # -- la fusion
    banc.js("fusionner(A, B, maxPrisesPartout(plan(A))); closeSheet(); renderAll()"); time.sleep(0.3)
    essais.verifier('mes prises du B passent sur A, a la suite : 4 et 5',
                    banc.js("prisesDe(A).map(t => t.n + ' ' + t.clip).sort()"), ['1 SA1', '4 SB1', '5 SB2'])
    essais.verifier('elles gardent d ou elles viennent', banc.js("prisesDe(A).find(t => t.clip === 'SB1').notes"), 'prise 1 du shot ' + db['plans'][1]['plan'])
    essais.verifier('le B : abandonne, fusionne dans A, sans prise', [banc.js("plan(B).etat"), banc.js("plan(B).fusionDans === A"), banc.js("prisesDe(B).length")], ['drop', True, 0])
    essais.verifier('les textes et elements du B rejoignent A, ceux de chacun',
                    [banc.js("plan(A)['vfxDesc@Romain']"), banc.js("plan(A)['vfxDesc@Simon']"), banc.js("elementsDe(plan(A), 'Romain', false)")],
                    ['Reflet a effacer', 'Pied de micro', {'hdri': True}])
    essais.verifier('la note commune de A le dit', 'Tourné avec le shot' in banc.js("plan(A).notesClient"), True)
    essais.verifier('la liste : « + » sur A, « fusionne dans » sur B',
                    [banc.js("document.querySelector('#l-shoot .plan[data-id=\"' + A + '\"] .pno-plus').textContent.indexOf('+') === 0"),
                     banc.js("document.querySelector('#l-shoot .plan[data-id=\"' + B + '\"] .pfusion').textContent.indexOf('fusionné dans') === 0")], [True, True])
    patienter(lambda: len([t for t in api('etat.php?espace=simon')['db']['prises'] if t['planId'] == a]) == 3, tours=40)
    essais.verifier('le serveur a mes prises sur A', sorted(t['n'] for t in api('etat.php?espace=simon')['db']['prises'] if t['planId'] == a), [1, 4, 5])
    essais.verifier('la fusion est arrivee chez Romain (le plan est partage)', api('etat.php?espace=romain')['db']['plans'][1].get('fusionDans'), a)
    essais.verifier('ses prises attendent son appareil', prises_romain(b), [(1, 'RB1'), (2, 'RB2')])

    # -- l'appareil de Romain retrouve son espace : il deplace les siennes, avec le meme decalage
    banc.js("changerDePersonne('Romain')")
    essais.verifier('chez Romain, les prises du B passent sur A : 4 et 5',
                    patienter(lambda: prises_romain(a) == [(1, 'RA1'), (2, 'RA2'), (3, 'RA3'), (4, 'RB1'), (5, 'RB2')], tours=60, pause=0.5), True)
    essais.verifier('et plus rien sur le B', prises_romain(b), [])
    banc.js("openPlan(B)"); time.sleep(0.3)
    essais.verifier('la fiche du B dit ou il est passe', 'Fusionné dans le' in banc.js("$('sbody').textContent"), True)
    essais.exceptions(banc)
essais.bilan()
