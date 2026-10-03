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
    essais.verifier('la barre est dans la marge : l etiquette du diaph s aligne sur les autres',
                    banc.js("(() => { const x = k => Math.round(document.querySelector('#sbody [data-k=\"' + k + '\"]').closest('.spec').querySelector('label').getBoundingClientRect().left); return x('diaph') - x('mesureDepuis'); })()"), 0)
    essais.verifier('resultat : son NG porte son initiale', bulle(banc, '#seg-statut button[data-st="NG"]'), 'a2-lui R')
    essais.verifier('note rapide : sa bulle Raccord aussi', bulle(banc, '.chips-notes button[data-n="Raccord"]'), 'a2-lui R')
    essais.verifier('meteo : sa valeur dans l en-tete de la ligne',
                    banc.js("(() => { const c = document.querySelector('.champ[data-champ=\"meteo\"]'); return [c.className.split(' ').find(x => x.indexOf('a2-') === 0), c.querySelector('.a2-pts').textContent]; })()"),
                    ['a2-autre', 'RSoleil'])

    # dans la liste : la meme prise chez Romain, un autre clip -> l'ecart s'y lit
    banc.js("patch('prise', openId, { clip: 'A_0001C009' }); renderList()")
    ligne = lambda: banc.js("(() => { const r = document.querySelector('.prise[data-id=\"' + openId + '\"] .accord'); return r ? r.className + ' | ' + r.textContent.replace(/\\s+/g, ' ').trim() : ''; })()")
    essais.verifier('la liste : un autre clip chez Romain, signale', ligne(), 'accord non | ⚠ RA_0001C001')
    banc.js("patch('prise', openId, { clip: '' }); renderList()")
    # Simon confirme : il reprend le clip, marque NG, touche Raccord
    banc.js("document.querySelector('#sbody [data-k=\"clip\"]').closest('.spec, .clip').nextElementSibling.querySelector('button').click()")
    essais.verifier('un appui reprend son clip', [banc.js("prise(openId).clip"), spec(banc, 'clip')], ['A_0001C001', 'a2-accord'])
    banc.js("renderList()")
    essais.verifier('la liste : meme clip chez Romain, coche verte', ligne(), 'accord oui | ✓ R')
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
    # les elements sont a chacun : le HDRI de Romain porte son rond, il n'est pas coche chez Simon
    essais.verifier('fiche du plan : le HDRI de Romain porte son rond, pas coche chez Simon', bulle(banc, '.el[data-el="hdri"]'), 'a2-lui R')
    essais.verifier('et il n est pas dans les elements de Simon', banc.js("!!mesElements(plan(openId)).hdri"), False)
    banc.js("toggleElement('chart')")
    essais.verifier('la charte, cochee par Simon : sous son prenom, sans rond', [banc.js("plan(openId)['elements@Simon']"), bulle(banc, '.el[data-el="chart"]')], [{'chart': True}, ''])
    essais.verifier('cocher la sienne ne touche pas au HDRI de Romain', banc.js("elementsDe(plan(openId), 'Romain', false)"), {'hdri': True})
    banc.js("toggleElement('hdri')")
    essais.verifier('Simon coche le HDRI aussi : a deux, entoure de vert', bulle(banc, '.el[data-el="hdri"]'), 'a2-deux R')
    banc.js("toggleElement('hdri')")
    essais.verifier('Simon le decoche : celui de Romain reste', [bulle(banc, '.el[data-el="hdri"]'), banc.js("elementsTous(plan(openId)).hdri")], ['a2-lui R', True])
    romain([{'op': 'patch', 'kind': 'plan', 'id': pid, 'data': {'elements@Romain': {'hdri': True, 'lidar': True}}}])
    essais.verifier('Romain coche le Lidar de son cote : son rond, et la charte de Simon reste',
                    patienter(lambda: bulle(banc, '.el[data-el="lidar"]') == 'a2-lui R' and banc.js("!!mesElements(plan(openId)).chart"), tours=40), True)
    essais.verifier('la liste, les filtres et les PDF voient les elements de tous', sorted(banc.js("Object.keys(elementsTous(plan(openId)))")), ['chart', 'hdri', 'lidar'])
    essais.verifier('les elements que personne n a coches : rien', banc.js("document.querySelectorAll('#sbody .el:not(.on):not(.a2-lui) .a2-pt').length"), 0)
    essais.verifier('l anneau du Moteur a cote de la description', banc.js("!!document.querySelector('#sbody .lead-ligne .viser[data-vise=\"' + openId + '\"]')"), True)
    essais.verifier('pas de bandeau sur un plan : il n y a rien a comparer', banc.js("!!document.querySelector('#sbody .a2-tete')"), False)
    # le contexte commun : le rond de Romain sur ce qu'il a choisi, pas sur le nom du champ
    romain([{'op': 'patch', 'kind': 'plan', 'id': pid, 'data': {'momentJour': 'Aube', 'auteurs': {'el:hdri': 'Romain', 'momentJour': 'Romain'}}}])
    patienter(lambda: banc.js("plan(openId).momentJour") == 'Aube', tours=40)
    banc.js("ouvrirChamp('momentJour'); decorerFiche()")
    essais.verifier('contexte : pas de rond a cote du nom du champ',
                    banc.js("document.querySelectorAll('.champ[data-champ=\"momentJour\"] .champ-nom .a2-pt').length"), 0)
    essais.verifier('contexte : son rond a cote de la valeur',
                    banc.js("(document.querySelector('.champ[data-champ=\"momentJour\"] .champ-val .a2-pts') || {}).textContent"), 'R')
    essais.verifier('contexte : la tuile Aube porte son rond', bulle(banc, '.champ[data-champ="momentJour"] .tuile[data-f="Aube"]'), 'a2-lui R')
    essais.verifier('contexte : les autres tuiles, rien', bulle(banc, '.champ[data-champ="momentJour"] .tuile[data-f="Nuit"]'), '')
    # la note du plan est a chacun : celle de Romain en italique sous la sienne
    essais.verifier('sa note a lui, en italique sous la mienne',
                    banc.js("[...document.querySelectorAll('.textes-autres[data-texte=\"notesClient\"] .texte-autre')].map(d => d.querySelector('b').textContent + ' | ' + d.querySelector('i').textContent)"),
                    ['Romain | Reflets sur la vitre'])
    banc.js("const n = document.querySelector('#sbody textarea[data-k=\"notesClient@Simon\"]'); n.value = 'Pluie annoncee'; live(n)")
    essais.verifier('ma note porte mon rond, a cote de l etiquette',
                    banc.js("(document.querySelector('#sbody textarea[data-k=\"notesClient@Simon\"]').closest('.spec').querySelector('.a2-pt.moi') || {}).textContent"), 'S')
    essais.verifier('ma description, vide : pas de rond',
                    banc.js("!!document.querySelector('#sbody [data-k=\"vfxDesc@Simon\"]').closest('.spec').querySelector('.a2-pt.moi')"), False)
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
    # la fiche du plan ouverte, les saisies de Romain arrivent : le rond de l'anneau ne clignote pas
    banc.js("openPlan(%s); window.__rond = document.querySelector('#sbody .viser .a2-pt')" % json.dumps(pid2))
    essais.verifier('dans la fiche du plan aussi, a cote de la description', banc.js("!!window.__rond"), True)
    banc.js("majFicheEnPlace(); decorerFiche(); majVise(); rafraichirDoux()")
    essais.verifier('la fiche se met a jour : le meme rond, jamais efface puis repose',
                    banc.js("document.querySelector('#sbody .viser .a2-pt') === window.__rond && document.body.contains(window.__rond)"), True)
    banc.js("closeSheet()")
    banc.js("viser(%s)" % json.dumps(pid2))
    essais.verifier('Simon vise a son tour : le serveur le sait',
                    patienter(lambda: any(x['nom'] == 'Simon' and ('vise:' + pid2) in x['actif'] for x in api('depuis.php?rev=0&client=x&espace=simon')['presence']), tours=40), True)
    api('presence.php', {'client': 'romain1', 'nom': 'Romain', 'actif': '', 'espace': 'romain'})
    essais.verifier('Romain passe a autre chose : son rond s en va',
                    patienter(lambda: banc.js("document.querySelectorAll('.viser .a2-pt').length") == 0, tours=40), True)

    # -- la presence : Romain sur deux onglets (un navigateur relance) ne compte qu'une fois
    for c in ('romain-ancien', 'romain-neuf'):
        api('presence.php', {'client': c, 'nom': 'Romain', 'actif': 'plan:' + pid2, 'espace': 'romain'})
    time.sleep(1.5)
    essais.verifier('la carte du shot ne porte plus l initiale de qui l a ouvert',
                    banc.js("document.querySelectorAll('.plan[data-id=\"%s\"] .pnum .qui').length" % pid2), 0)
    essais.verifier('et le compte dit des personnes, pas des onglets', banc.js("personnesConnectees().map(x => x.nom).filter(Boolean).sort()"), ['Romain', 'Simon'])
    api('presence.php', {'client': 'romain-ancien', 'quitte': True, 'espace': 'romain'})
    essais.verifier('un onglet ferme sort de la liste tout de suite',
                    [x['client'] for x in api('depuis.php?rev=0&client=x&espace=simon')['presence'] if x['client'].startswith('romain-')], ['romain-neuf'])

    import base64
    banc.js("openPrise(DB.prises.find(t => t.n === 1).id)"); time.sleep(0.5)
    if os.environ.get('CAPTURE'):
        open(os.environ['CAPTURE'], 'wb').write(base64.b64decode(banc.cdp.appel('Page.captureScreenshot', format='png')['data']))
    essais.exceptions(banc)
essais.bilan()
