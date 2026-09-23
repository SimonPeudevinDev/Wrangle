# -*- coding: utf-8 -*-
"""Le journal DIT par mail : la page fabrique le PDF, le serveur l'expedie par
la boite reglee dans data/mail.json. A la main, ou a l'heure dite, une seule
fois par journee meme si plusieurs appareils le tentent."""
import email
import email.policy
import json
import os
import socket
import socketserver
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banc import Banc, Essais                                     # noqa: E402

RECUS = []          # les messages arrives sur la boite factice : (expediteur, destinataires, octets)


class Boite(socketserver.StreamRequestHandler):
    """Un serveur SMTP tout juste assez poli pour recevoir un message."""
    def handle(self):
        def dire(s): self.wfile.write((s + '\r\n').encode())
        dire('220 boite factice')
        de, a, donnees = '', [], None
        while True:
            ligne = self.rfile.readline()
            if not ligne:
                return
            l = ligne.decode('utf-8', 'replace').rstrip('\r\n')
            if donnees is not None:
                if l == '.':
                    RECUS.append((de, a, b''.join(donnees)))
                    donnees = None
                    dire('250 OK')
                else:
                    donnees.append(ligne)
                continue
            cmd = l.split(' ')[0].upper()
            if cmd in ('EHLO', 'HELO'): dire('250-boite'); dire('250 OK')
            elif cmd == 'MAIL': de = l.split(':', 1)[1].strip(); dire('250 OK')
            elif cmd == 'RCPT': a.append(l.split(':', 1)[1].strip().strip('<>')); dire('250 OK')
            elif cmd == 'DATA': donnees = []; dire('354 allez-y')
            elif cmd == 'QUIT': dire('221 au revoir'); return
            elif cmd == 'RSET': de, a = '', []; dire('250 OK')
            else: dire('250 OK')


def port_libre():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


PORT_SMTP = port_libre()
boite = socketserver.ThreadingTCPServer(('127.0.0.1', PORT_SMTP), Boite)
boite.daemon_threads = True
threading.Thread(target=boite.serve_forever, daemon=True).start()

essais = Essais(largeur=58)
with Banc(8781, 9381, taille=(1100, 900)) as banc:
    banc.ouvrir()
    banc.nommer()
    chemin_cfg = os.path.join(banc.data, 'mail.json')

    def attendre(expr):
        r = banc.cdp.appel('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
        return r.get('result', {}).get('value')

    # -- sans boite, l'envoi est refuse proprement
    banc.js("ajouterPrise(DB.plans[0].id, false, { clip:'A001C001', carte:'A001', statut:'OK', retenue:true, par:'Bob', heure:'09:15' });"
            " patch('prod', 'prod', { mailA:'post@prod.fr; montage@prod.fr', mailHeure:'20h' })")
    etat = json.loads(urllib.request.urlopen('http://localhost:8781/api/mail', timeout=5).read())
    essais.verifier('le serveur dit qu il n a pas de boite', etat['possible'], False)
    rep = attendre("envoyerJournalMail(false)")
    essais.verifier('sans boite, le serveur refuse', 'erreur' in (rep or {}), True)
    time.sleep(0.3)
    essais.verifier('et la page le dit', banc.js("$('dlg-titre').textContent"), 'Le journal n’est pas parti.')
    banc.js("fermerDialogue(false)")

    # -- la boite reglee : l'envoi a la main part, avec le PDF en piece jointe
    json.dump({'smtp': '127.0.0.1', 'port': PORT_SMTP, 'securite': 'aucune', 'expediteur': 'Wrangle <journal@test.fr>'},
              open(chemin_cfg, 'w', encoding='utf-8'))
    rep = attendre("envoyerJournalMail(false)")
    essais.verifier('l envoi a la main part', (rep or {}).get('ok'), True)
    essais.verifier('aux deux adresses, separees par un point-virgule', rep.get('a'), ['post@prod.fr', 'montage@prod.fr'])
    essais.verifier('la boite a recu un message', len(RECUS), 1)
    de, a, brut = RECUS[0]
    msg = email.message_from_bytes(brut, policy=email.policy.default)
    essais.verifier('de la part de la boite reglee', 'journal@test.fr' in de, True)
    essais.verifier('pour les deux destinataires', sorted(a), ['montage@prod.fr', 'post@prod.fr'])
    sujet = str(msg['Subject'])
    essais.verifier('le sujet nomme le projet, le journal et la journee', 'Foresight' in sujet and 'journal DIT de jour 1' in sujet, True)
    pj = [p for p in msg.walk() if p.get_content_type() == 'application/pdf']
    essais.verifier('un PDF en piece jointe', len(pj), 1)
    essais.verifier('qui est bien le journal', pj[0].get_payload(decode=True)[:5], b'%PDF-')
    essais.verifier('nomme d apres le projet et la journee', pj[0].get_filename().endswith('journal-DIT-J1.pdf'), True)
    essais.verifier('le texte du mail dit ce qu il contient', 'prises retenues' in msg.get_body(preferencelist=('plain',)).get_content(), True)
    time.sleep(0.4)
    essais.verifier('la page note le dernier envoi pour tous', 'Jour 1' in banc.js('DB.prod.mailDernier'), True)
    essais.verifier('et le dit', banc.js("$('toast-msg').textContent"), 'Journal envoyé à post@prod.fr, montage@prod.fr')

    # -- les creneaux : toutes les heures a l'heure pile dans la plage, les journees cochees
    banc.js("patch('prod', 'prod', { mailCadence:'1h', mailDebut:'8h', mailFin:'20:00', mailJours:[] })")
    essais.verifier('a 14 h pile, un creneau', banc.js("creneauMail(new Date(2026, 8, 23, 14, 0))"), '2026-09-23 J1 14h')
    essais.verifier('a 14 h 05, rien', banc.js("creneauMail(new Date(2026, 8, 23, 14, 5))"), '')
    essais.verifier('a 22 h, hors plage, rien', banc.js("creneauMail(new Date(2026, 8, 23, 22, 0))"), '')
    essais.verifier('toutes les deux heures : 15 h passe son tour',
                    banc.js("patch('prod','prod',{mailCadence:'2h'}); [creneauMail(new Date(2026,8,23,14,0)), creneauMail(new Date(2026,8,23,15,0))]"),
                    ['2026-09-23 J1 14h', ''])
    essais.verifier('une fois par jour, a l heure dite',
                    banc.js("patch('prod','prod',{mailCadence:'jour', mailHeure:'20h'}); [creneauMail(new Date(2026,8,23,20,0)), creneauMail(new Date(2026,8,23,19,0))]"),
                    ['2026-09-23 J1', ''])
    essais.verifier('avant la date de debut, rien ne part',
                    banc.js("patch('prod','prod',{mailCadence:'1h', mailDu:'2026-09-24', mailAu:'2026-09-30'}); creneauMail(new Date(2026,8,23,14,0))"), '')
    essais.verifier('apres la date de fin non plus',
                    banc.js("patch('prod','prod',{mailDu:'2026-09-01', mailAu:'2026-09-22'}); creneauMail(new Date(2026,8,23,14,0))"), '')
    essais.verifier('entre les deux dates, oui',
                    banc.js("patch('prod','prod',{mailDu:'2026-09-20', mailAu:'2026-09-30'}); creneauMail(new Date(2026,8,23,14,0))"), '2026-09-23 J1 14h')
    essais.verifier('l heure s ecrit comme on veut', banc.js("heureLue('8h5')"), '08:05')

    # -- l'envoi automatique : une fois par creneau, et seulement s'il y a du nouveau
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'A001C002', statut:'NG', par:'Alice', heure:'13:40' })")
    attendre("verifierEnvoiAuto(new Date(2026, 8, 23, 14, 0))")
    essais.verifier('a l heure pile, le journal part tout seul', len(RECUS), 2)
    rep = attendre("verifierEnvoiAuto.fait = null; patch('prod','prod',{ mailEmpreinte:'' }); verifierEnvoiAuto(new Date(2026, 8, 23, 14, 0))")
    essais.verifier('un second appareil au meme creneau ne renvoie pas', len(RECUS), 2)
    essais.verifier('et le serveur le lui dit', (rep or {}).get('deja'), True)
    banc.js("patch('prod','prod',{ mailEmpreinte: empreinteMail() })")   # l'empreinte du dernier envoi, telle qu'elle serait restee
    attendre("verifierEnvoiAuto(new Date(2026, 8, 23, 15, 0))")
    essais.verifier('l heure d apres, sans rien de neuf, rien ne part', len(RECUS), 2)
    banc.js("ajouterPrise(DB.plans[1].id, false, { clip:'A001C003', statut:'OK', par:'Alice', heure:'15:40' })")
    attendre("verifierEnvoiAuto(new Date(2026, 8, 23, 16, 0))")
    essais.verifier('une prise de plus : le journal suivant part', len(RECUS), 3)
    etat = json.loads(urllib.request.urlopen('http://localhost:8781/api/mail', timeout=5).read())
    essais.verifier('le serveur tient le journal des envois', [(e['auto'], e['cle']) for e in etat['envois']],
                    [(False, ''), (True, '2026-09-23 J1 14h'), (True, '2026-09-23 J1 16h')])

    # -- la fiche Journee montre les reglages et la boite
    banc.js("openProd()"); time.sleep(0.8)
    essais.verifier('la fiche Journee a ses reglages de mail', banc.js(
        "!!document.querySelector('#sbody textarea[data-k=\"mailA\"]') && !!document.querySelector('#sbody select[data-k=\"mailCadence\"]')"
        " && document.querySelectorAll('#plage-mail input[type=range]').length === 2"
        " && !!document.querySelector('#sbody input[data-k=\"mailDu\"]') && !!document.querySelector('#sbody input[data-k=\"mailAu\"]')"), True)

    # -- le calendrier de la page, a la place de celui du navigateur
    essais.verifier('les dates s ecrivent a la francaise', banc.js("document.querySelector('#sbody input[data-k=\"mailDu\"]').value"), '20/09/2026')
    banc.js("document.querySelector('#sbody input[data-k=\"mailDu\"]').click()"); time.sleep(0.3)
    essais.verifier('toucher la date ouvre le calendrier, sur son mois', banc.js("document.querySelector('.calendrier .ctete b').textContent"), 'Septembre 2026')
    essais.verifier('lundi en tete, six semaines', banc.js("[...document.querySelectorAll('.calendrier .cjours span')].map(s => s.textContent).join('') + document.querySelectorAll('.calendrier .j').length"), 'LMMJVSD42')
    essais.verifier('la date choisie et la periode jusqu a l autre borne',
                    banc.js("[document.querySelector('.calendrier .j.on').dataset.d, document.querySelector('.calendrier .j.borne').dataset.d, document.querySelectorAll('.calendrier .j.entre').length]"),
                    ['2026-09-20', '2026-09-30', 9])
    banc.js("bougerMois(1)")
    essais.verifier('le mois suivant', banc.js("document.querySelector('.calendrier .ctete b').textContent"), 'Octobre 2026')
    banc.js("document.querySelector('.calendrier .j[data-d=\"2026-10-05\"]').click()"); time.sleep(0.3)
    essais.verifier('choisir un jour pose la date et referme', [banc.js('DB.prod.mailDu'), banc.js("!!document.querySelector('.calendrier')"),
                    banc.js("document.querySelector('#sbody input[data-k=\"mailDu\"]').value")], ['2026-10-05', False, '05/10/2026'])
    banc.js("document.querySelector('#sbody input[data-k=\"mailAu\"]').click()"); time.sleep(0.3)
    banc.js("document.dispatchEvent(new KeyboardEvent('keydown', { key:'Escape', bubbles:true }))"); time.sleep(0.2)
    essais.verifier('Echap referme le calendrier', banc.js("!!document.querySelector('.calendrier')"), False)
    essais.verifier('le curseur ecrit la plage', banc.js("$('plage-txt').textContent"), '08:00 → 20:00')
    banc.js("""(() => { const r = document.querySelectorAll('#plage-mail input[type=range]'); r[1].value = 6; glisserPlage(r[1]); })()""")
    essais.verifier('la fin ne passe pas avant le debut : elle pousse', [banc.js('DB.prod.mailDebut'), banc.js('DB.prod.mailFin'), banc.js("$('plage-txt').textContent")],
                    ['06:00', '06:00', '06:00 → 06:00'])
    banc.js("""(() => { const r = document.querySelectorAll('#plage-mail input[type=range]'); r[1].value = 18; glisserPlage(r[1]); })()""")
    essais.verifier('et se regle au curseur', [banc.js('DB.prod.mailDebut'), banc.js('DB.prod.mailFin')], ['06:00', '18:00'])
    essais.verifier('et dit quelle boite envoie', 'journal@test.fr' in banc.js("$('mail-etat').textContent"), True)
    essais.exceptions(banc)
boite.shutdown()
essais.bilan()
