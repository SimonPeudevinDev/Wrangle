# -*- coding: utf-8 -*-
"""Ce que les autres ont note, dans la fiche. Romain a note la prise 1 d'un
plan (clip, carte, diaph, resultat, note rapide, meteo) et un element capte
sur le plan ; Simon ouvre la meme prise. Chaque ligne dit qui l'a remplie :
barre a la couleur de Romain quand lui seul l'a fait, verte quand ils
concordent, rouge quand ils different ; la valeur de Romain se reprend d'un
appui. Les bulles portent son initiale, et s'entourent de vert choisies a
deux. Ce que Romain change ensuite arrive dans la fiche ouverte. La page est
en mode « php »."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais, patienter                         # noqa: E402

PORT = 8789


def api(chemin, corps=None):
    url = 'http://localhost:%d/api/%s' % (PORT, chemin)
    if corps is None:
        return json.loads(urllib.request.urlopen(url, timeout=5).read())
    req = urllib.request.Request(url, data=json.dumps(corps).encode('utf-8'), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


def romain(liste):
    return api('ops.php', {'client': 'romain1', 'nom': 'Romain', 'espace': 'romain', 'ops': liste})


def spec(banc, k):
    """La classe a2 de la ligne du champ k, et ce que dit la ligne dessous."""
    return banc.js("""(() => { const s = document.querySelector('#sbody [data-k="%s"]').closest('.spec, .clip');
      const c = [...s.classList].find(x => x.indexOf('a2-') === 0) || '';
      const r = s.nextElementSibling && s.nextElementSibling.classList.contains('a2-row')
        ? [...s.nextElementSibling.querySelectorAll('.a2-val')].map(b => [...b.children].map(x => x.textContent).join(' ')).join(' / ') : '';
      return c + (r ? ' | ' + r : ''); })()""" % k)


def bulle(banc, sel):
    return banc.js("""(() => { const b = document.querySelector(%s); if (!b) return 'absente';
      return [...b.classList].filter(x => x.indexOf('a2-') === 0).join(' ') + ' ' + [...b.querySelectorAll('.a2-pt')].map(x => x.textContent).join(''); })()""" % json.dumps(sel)).strip()


essais = Essais(largeur=64)
with Banc(PORT, 9389, taille=(420, 900)) as banc:
    banc.vue(390, 844)
    banc.ouvrir('/?php=1')
    banc.nommer()                                    # Simon
    patienter(lambda: banc.js("RESEAU.etat === 'ok' && RESEAU.rev >= 1 && !RESEAU.attente.length"), tours=60)
    db = api('etat.php?espace=simon')['db']
    pid = db['plans'][0]['id']
    romain([{'op': 'remplacer', 'db': dict(db, prises=[])},
            {'op': 'add', 'kind': 'prise', 'data': {'id': 'r1', 'planId': pid, 'n': 1, 'par': 'Romain', 'clip': 'A_0001C001',
                                                     'carte': 'A_0001', 'diaph': 'T4', 'statut': 'NG', 'notes': 'Raccord',
                                                     'meteo': 'Soleil', 'heure': '09:12'}},
            # comme la page : l'element coche, et qui l'a coche ; puis sa note a lui sur le plan
            {'op': 'patch', 'kind': 'plan', 'id': pid, 'data': {'elements': {'hdri': True}, 'auteurs': {'el:hdri': 'Romain'},
                                                                 'notesClient@Romain': 'Reflets sur la vitre'}}])

    # Simon a sa propre prise 1 sur ce plan : meme carte, un autre diaph, pas de clip
    banc.js("var t = ajouterPrise(%s); patch('prise', t.id, {carte:'A_0001', diaph:'T2.8', heure:'09:13'}); openPrise(t.id)" % json.dumps(pid))
    banc.js("majAutres(true)")
    essais.verifier('la fiche dit que Romain a aussi note cette prise',
                    patienter(lambda: 'Romain' in (banc.js("(document.querySelector('#sbody .a2-tete') || {}).textContent || ''")), tours=40), True)
    essais.verifier('clip : Romain seul, sa valeur a reprendre', spec(banc, 'clip'), 'a2-autre | R A_0001C001 reprendre')
    essais.verifier('carte : la meme, barre verte, rien dessous', spec(banc, 'carte'), 'a2-accord')
    essais.verifier('diaph : un ecart, barre rouge et sa valeur', spec(banc, 'diaph'), 'a2-ecart | R T4 reprendre')
    essais.verifier('heure : ce n est pas un desaccord', spec(banc, 'heure'), '')
    essais.verifier('resultat : son NG porte son initiale', bulle(banc, '#seg-statut button[data-st="NG"]'), 'a2-lui R')
    essais.verifier('note rapide : sa bulle Raccord aussi', bulle(banc, '.chips-notes button[data-n="Raccord"]'), 'a2-lui R')
    essais.verifier('meteo : sa valeur dans l en-tete de la ligne',
                    banc.js("(() => { const c = document.querySelector('.champ[data-champ=\"meteo\"]'); return [c.className.split(' ').find(x => x.indexOf('a2-') === 0), c.querySelector('.a2-pts').textContent]; })()"),
                    ['a2-autre', 'RSoleil'])

    # Simon confirme : il reprend le clip, marque NG, touche Raccord
    banc.js("document.querySelector('#sbody [data-k=\"clip\"]').closest('.spec, .clip').nextElementSibling.querySelector('button').click()")
    essais.verifier('un appui reprend son clip', [banc.js("prise(openId).clip"), spec(banc, 'clip')], ['A_0001C001', 'a2-accord'])
    banc.js("marquer(openId, 'NG'); noteRapide('Raccord')")
    essais.verifier('NG choisi a deux : entoure de vert', bulle(banc, '#seg-statut button[data-st="NG"]'), 'a2-deux R')
    essais.verifier('Raccord choisi a deux', bulle(banc, '.chips-notes button[data-n="Raccord"]'), 'a2-deux R')
    essais.verifier('sa note n est plus proposee : elle est dans la mienne', spec(banc, 'notes'), 'a2-accord')
    banc.js("ouvrirChamp('meteo')")
    essais.verifier('la tuile Soleil porte son initiale', bulle(banc, '.champ[data-champ="meteo"] .tuile[data-f="Soleil"]'), 'a2-lui R')
    banc.js("choisirChamp('meteo', 'Soleil')")
    essais.verifier('choisie aussi : la ligne meteo concorde', banc.js("document.querySelector('.champ[data-champ=\"meteo\"]').className.indexOf('a2-accord') >= 0"), True)

    # ce que Romain change ensuite arrive dans la fiche ouverte
    romain([{'op': 'patch', 'kind': 'prise', 'id': 'r1', 'data': {'sonRoll': 'S012'}}])
    banc.js("majAutres(true)")
    essais.verifier('sa bande son, notee apres coup, arrive', patienter(lambda: spec(banc, 'sonRoll') == 'a2-autre | R S012 reprendre', tours=40), True)

    # le plan : son element capte
    banc.js("openPlan(%s)" % json.dumps(pid))
    # le plan est partage : le HDRI coche par Romain est chez Simon aussi, avec sa pastille a lui seul
    essais.verifier('fiche du plan : le HDRI porte la pastille de Romain, qui l a coche', bulle(banc, '.el[data-el="hdri"]'), 'a2-lui R')
    banc.js("toggleElement('chart')")
    essais.verifier('la charte, cochee par Simon lui-meme : pas de pastille', [banc.js("plan(openId).auteurs['el:chart']"), bulle(banc, '.el[data-el="chart"]')], ['Simon', ''])
    essais.verifier('les elements que personne n a coches : rien', banc.js("document.querySelectorAll('#sbody .el:not(.on) .a2-pt').length"), 0)
    essais.verifier('pas de bandeau sur un plan : il n y a rien a comparer', banc.js("!!document.querySelector('#sbody .a2-tete')"), False)
    # la note du plan est a chacun : celle de Romain en italique sous la sienne
    essais.verifier('sa note a lui, en italique sous la mienne',
                    banc.js("[...document.querySelectorAll('.textes-autres[data-texte=\"notesClient\"] .texte-autre')].map(d => d.querySelector('b').textContent + ' | ' + d.querySelector('i').textContent)"),
                    ['Romain | Reflets sur la vitre'])
    banc.js("const n = document.querySelector('#sbody textarea[data-k=\"notesClient@Simon\"]'); n.value = 'Pluie annoncee'; live(n)")
    essais.verifier('la mienne est rangee sous mon prenom, la sienne reste', [banc.js("plan(openId)['notesClient@Simon']"), banc.js("plan(openId)['notesClient@Romain']")], ['Pluie annoncee', 'Reflets sur la vitre'])
    essais.verifier('les PDF et exports lisent les deux', banc.js("texteDe(plan(openId), 'notesClient')"), 'Romain : Reflets sur la vitre · Simon : Pluie annoncee')

    # une prise que Romain n'a pas : rien a montrer
    banc.js("var u = ajouterPrise(%s); openPrise(u.id)" % json.dumps(pid))
    essais.verifier('prise 2, que Romain n a pas : rien', [banc.js("!!document.querySelector('#sbody .a2-tete:not([hidden])')"), banc.js("document.querySelectorAll('#sbody .a2-row, #sbody .a2-pt').length")], [False, 0])

    # -- le Moteur : Romain vise un plan, son rond apparait sur l'anneau de ce plan chez Simon
    banc.js("closeSheet()")
    pid2 = db['plans'][1]['id']
    api('presence.php', {'client': 'romain1', 'nom': 'Romain', 'actif': 'vise:' + pid2, 'espace': 'romain'})
    essais.verifier('Romain vise le plan 2 : son rond sur l anneau du Moteur',
                    patienter(lambda: banc.js("[...document.querySelectorAll('.viser[data-vise=\"%s\"] .a2-pt')].map(x => x.textContent).join()" % pid2) == 'R', tours=40), True)
    essais.verifier('et sur aucun autre plan', banc.js("document.querySelectorAll('.viser .a2-pt').length"), 1)
    banc.js("viser(%s)" % json.dumps(pid2))
    essais.verifier('Simon vise a son tour : le serveur le sait',
                    patienter(lambda: any(x['nom'] == 'Simon' and ('vise:' + pid2) in x['actif'] for x in api('depuis.php?rev=0&client=x&espace=simon')['presence']), tours=40), True)
    api('presence.php', {'client': 'romain1', 'nom': 'Romain', 'actif': '', 'espace': 'romain'})
    essais.verifier('Romain passe a autre chose : son rond s en va',
                    patienter(lambda: banc.js("document.querySelectorAll('.viser .a2-pt').length") == 0, tours=40), True)

    import base64
    banc.js("openPrise(DB.prises.find(t => t.n === 1).id)"); time.sleep(0.5)
    if os.environ.get('CAPTURE'):
        open(os.environ['CAPTURE'], 'wb').write(base64.b64decode(banc.cdp.appel('Page.captureScreenshot', format='png')['data']))
    essais.exceptions(banc)
essais.bilan()
