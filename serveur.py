#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRANGLE — serveur de plateau.

Un seul fichier, bibliothèque standard uniquement (Python 3.8+).

  py serveur.py            démarre sur le port 8765
  py serveur.py 9000       autre port
  py serveur.py --ouvrir   démarre et ouvre le navigateur
  py serveur.py --data D:\autre\dossier   range projet.json et les sauvegardes ailleurs

Le serveur :
  - sert la page wrangle.html et le dossier public/ (feuille de style, logo) ;
  - garde l'état partagé du projet (data/projet.json) ;
  - reçoit les modifications de chaque appareil (POST /api/ops) sous forme
    d'opérations champ par champ, les applique et les rediffuse à tous les
    appareils connectés par flux SSE (GET /api/flux) ;
  - tient la liste des personnes connectées et ce qu'elles regardent ;
  - fait une sauvegarde horodatée dans data/sauvegardes/ toutes les 10 min
    dès que quelque chose a changé (60 dernières conservées).

Tous les appareils doivent être sur le même réseau (Wi-Fi du plateau) et
ouvrir l'adresse affichée au démarrage.
"""

import json
import os
import queue
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ICI, 'wrangle.html')
DATA = os.path.join(ICI, 'data')
FICHIER = os.path.join(DATA, 'projet.json')
SAUV = os.path.join(DATA, 'sauvegardes')
SAUV_TOUTES_LES = 10 * 60      # secondes entre deux sauvegardes horodatées
SAUV_CONSERVEES = 60
PRESENCE_EXPIRE = 90           # secondes sans nouvelle d'un client avant retrait

COLLECTIONS = {'plan': 'plans', 'prise': 'prises'}

# ----------------------------------------------------------------- État ---

verrou = threading.RLock()
etat = {'db': None, 'rev': 0, 'sale': False, 'derniere_sauv': 0.0}
abonnes = []          # files SSE : {'q': Queue, 'client': id}
presence = {}         # client -> {'nom', 'actif', 'vu'}
t_ecriture = None


def normaliser(db):
    """Garantit la forme du projet, quelle que soit la version du fichier."""
    if not isinstance(db, dict):
        db = {}
    db.setdefault('version', 2)
    db.setdefault('prod', {})
    db.setdefault('optiques', [])
    for c in ('plans', 'prises'):
        if not isinstance(db.get(c), list):
            db[c] = []
    db.pop('ui', None)           # préférence d'affichage : propre à chaque appareil
    for p in db['plans']:
        if isinstance(p, dict) and not isinstance(p.get('elements'), dict):
            p['elements'] = {}
    return db


def charger():
    if os.path.exists(FICHIER):
        try:
            with open(FICHIER, 'r', encoding='utf-8') as f:
                etat['db'] = normaliser(json.load(f))
            print('Projet chargé :', FICHIER,
                  '(%d plans, %d prises)' % (
                      len(etat['db']['plans']), len(etat['db']['prises'])))
        except Exception as e:  # fichier abîmé : on le met de côté, on ne l'écrase pas
            cote = FICHIER + '.illisible-' + datetime.now().strftime('%Y%m%d-%H%M%S')
            os.replace(FICHIER, cote)
            print('Projet illisible, mis de côté :', cote, '(', e, ')')
    else:
        print('Aucun projet enregistré : le premier appareil connecté enverra le sien.')


def ecrire_maintenant():
    """Écriture atomique : fichier temporaire puis remplacement."""
    global t_ecriture
    with verrou:
        t_ecriture = None
        if etat['db'] is None:
            return
        os.makedirs(DATA, exist_ok=True)
        tmp = FICHIER + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(etat['db'], f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, FICHIER)
        etat['sale'] = True


def planifier_ecriture():
    global t_ecriture
    with verrou:
        if t_ecriture is None:
            t_ecriture = threading.Timer(0.4, ecrire_maintenant)
            t_ecriture.daemon = True
            t_ecriture.start()


def sauvegarde_horodatee(force=False):
    with verrou:
        if etat['db'] is None or (not etat['sale'] and not force):
            return
        os.makedirs(SAUV, exist_ok=True)
        nom = os.path.join(SAUV, 'projet_' + datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.json')
        with open(nom, 'w', encoding='utf-8') as f:
            json.dump(etat['db'], f, ensure_ascii=False, separators=(',', ':'))
        etat['sale'] = False
        etat['derniere_sauv'] = time.time()
        anciennes = sorted(x for x in os.listdir(SAUV) if x.startswith('projet_') and x.endswith('.json'))
        for x in anciennes[:-SAUV_CONSERVEES]:
            try:
                os.remove(os.path.join(SAUV, x))
            except OSError:
                pass


def boucle_entretien():
    """Sauvegardes horodatées et nettoyage des présences fantômes."""
    while True:
        time.sleep(15)
        try:
            if time.time() - etat['derniere_sauv'] >= SAUV_TOUTES_LES:
                sauvegarde_horodatee()
            maintenant = time.time()
            with verrou:
                perimes = [c for c, p in presence.items() if maintenant - p['vu'] > PRESENCE_EXPIRE]
                for c in perimes:
                    del presence[c]
            if perimes:
                diffuser(message_presence())
        except Exception as e:
            print('Entretien :', e)


# ------------------------------------------------------------ Opérations ---

def trouver(db, kind, id_):
    coll = db.get(COLLECTIONS.get(kind, ''), None)
    if coll is None or not id_:
        return None
    for e in coll:
        if isinstance(e, dict) and e.get('id') == id_:
            return e
    return None


def appliquer(ops, client):
    """Applique les opérations d'un appareil. Retourne les opérations
    effectivement réalisées (parfois corrigées ou complétées)."""
    sortie = []
    db = etat['db']
    for op in ops:
        if not isinstance(op, dict):
            continue
        t = op.get('op')
        kind = op.get('kind')

        if t == 'remplacer':
            d = op.get('db')
            if not isinstance(d, dict) or 'plans' not in d:
                continue
            # envoi initial d'un appareil qui a trouvé le serveur vide : si un autre
            # appareil l'a devancé entre-temps, son projet reste, celui-ci est ignoré
            if op.get('siVide') and db is not None:
                continue
            etat['db'] = db = normaliser(d)
            sortie.append({'op': 'remplacer', 'db': db})
            continue

        if db is None:
            continue    # rien à modifier tant qu'aucun projet n'est chargé

        if t == 'patch':
            data = op.get('data')
            if not isinstance(data, dict):
                continue
            if kind == 'prod':
                db['prod'].update(data)
                sortie.append({'op': 'patch', 'kind': 'prod', 'data': data})
            else:
                e = trouver(db, kind, op.get('id'))
                if e is not None:
                    e.update(data)
                    sortie.append({'op': 'patch', 'kind': kind, 'id': op.get('id'), 'data': data})

        elif t == 'add':
            data = op.get('data')
            coll = db.get(COLLECTIONS.get(kind, ''), None)
            if coll is None or not isinstance(data, dict) or not data.get('id'):
                continue
            existant = trouver(db, kind, data['id'])
            if existant is not None:      # déjà reçu (renvoi après coupure) : simple mise à jour
                existant.update(data)
                sortie.append({'op': 'patch', 'kind': kind, 'id': data['id'], 'data': data})
                continue
            if kind == 'prise':
                # deux appareils peuvent ajouter une prise au même plan en même temps :
                # le serveur tranche sur le numéro
                freres = [p for p in coll if p.get('planId') == data.get('planId')]
                pris = {p.get('n') for p in freres}
                if not isinstance(data.get('n'), int) or data['n'] in pris:
                    data['n'] = (max([p.get('n') or 0 for p in freres]) + 1) if freres else 1
            # position d'un plan : apres tel plan, ou en tete ('' = avant tous)
            apres = op.get('apres')
            place = None
            if kind == 'plan' and apres is not None:
                if apres == '':
                    place = 0
                else:
                    for i, p in enumerate(coll):
                        if p.get('id') == apres:
                            place = i + 1
                            break
            if place is None:
                coll.append(data)
            else:
                coll.insert(place, data)
            res = {'op': 'add', 'kind': kind, 'data': data}
            if kind == 'plan' and apres is not None:
                res['apres'] = apres
            sortie.append(res)

        elif t == 'del':
            id_ = op.get('id')
            coll = db.get(COLLECTIONS.get(kind, ''), None)
            if coll is None or not id_:
                continue
            avant = len(coll)
            coll[:] = [e for e in coll if e.get('id') != id_]
            if len(coll) == avant:
                continue
            sortie.append({'op': 'del', 'kind': kind, 'id': id_})
            if kind == 'plan':
                orphelines = [p for p in db['prises'] if p.get('planId') == id_]
                for p in orphelines:
                    db['prises'].remove(p)
                    sortie.append({'op': 'del', 'kind': 'prise', 'id': p.get('id')})
            if kind == 'prise' and op.get('planId'):
                freres = sorted([p for p in db['prises'] if p.get('planId') == op['planId']],
                                key=lambda p: p.get('n') or 0)
                for i, p in enumerate(freres, 1):
                    if p.get('n') != i:
                        p['n'] = i
                        sortie.append({'op': 'patch', 'kind': 'prise', 'id': p['id'], 'data': {'n': i}})

        elif t == 'move':
            # un plan change de place : juste après tel plan, ou en tête ('' = avant tous)
            id_ = op.get('id')
            apres = op.get('apres', '')
            coll = db.get('plans') if kind == 'plan' else None
            if coll is None or not id_ or id_ == apres:
                continue
            bouge = [p for p in coll if p.get('id') == id_]
            if not bouge:
                continue
            coll.remove(bouge[0])
            place = 0
            if apres:
                for i, p in enumerate(coll):
                    if p.get('id') == apres:
                        place = i + 1
                        break
                else:
                    place = len(coll)
            coll.insert(place, bouge[0])
            sortie.append({'op': 'move', 'kind': 'plan', 'id': id_, 'apres': apres})

        elif t == 'optiques':
            liste = op.get('liste')
            if isinstance(liste, list):
                db['optiques'] = [str(x) for x in liste]
                sortie.append({'op': 'optiques', 'liste': db['optiques']})

    if sortie:
        etat['rev'] += 1
        planifier_ecriture()
    return sortie


# --------------------------------------------------------------- Diffusion ---

def diffuser(message, sauf=None):
    brut = 'data: ' + json.dumps(message, ensure_ascii=False) + '\n\n'
    with verrou:
        cibles = list(abonnes)
    for a in cibles:
        if sauf is not None and a['client'] == sauf:
            continue
        try:
            a['q'].put_nowait(brut)
        except queue.Full:
            pass


def message_presence():
    with verrou:
        liste = [{'client': c, 'nom': p.get('nom', ''), 'actif': p.get('actif', '')}
                 for c, p in presence.items()]
    return {'type': 'presence', 'liste': liste}


def noter_presence(client, nom=None, actif=None):
    if not client:
        return
    with verrou:
        p = presence.setdefault(client, {'nom': '', 'actif': '', 'vu': 0})
        if nom is not None:
            p['nom'] = str(nom)[:40]
        if actif is not None:
            p['actif'] = str(actif)[:80]
        p['vu'] = time.time()


def adresses_locales(port):
    """Les adresses à donner aux autres appareils du plateau."""
    ips = set()
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith('127.'):
                ips.add(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return ['http://%s:%d' % (ip, port) for ip in sorted(ips)]


# ------------------------------------------------------------------ HTTP ---

class Requete(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'FSTDW/2'

    def log_message(self, fmt, *args):
        pass    # silence : le journal ne montre que les événements utiles

    # -- utilitaires -------------------------------------------------------

    def _json(self, code, obj):
        corps = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(corps)))
        self.send_header('Cache-Control', 'no-store')
        self._cors()
        self.end_headers()
        self.wfile.write(corps)

    def _cors(self):
        # la page ouverte en fichier local (file://) peut envoyer son projet au serveur
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _lire_json(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > 64 * 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception:
            return None

    # -- GET ---------------------------------------------------------------

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ('/', '/index.html', '/wrangle.html'):
            return self._page()
        if u.path == '/api/etat':
            with verrou:
                return self._json(200, {'db': etat['db'], 'rev': etat['rev'],
                                        'presence': message_presence()['liste'],
                                        'adresses': self.server.adresses})
        if u.path == '/api/flux':
            return self._flux(parse_qs(u.query))
        for dossier in ('public', 'tests'):
            if u.path.startswith('/' + dossier + '/'):
                return self._statique(dossier, u.path[len(dossier) + 2:])
        self._json(404, {'erreur': 'introuvable'})

    def _statique(self, sous, nom):
        """Fichiers de public/ (feuille de style, logo) et de tests/."""
        dossier = os.path.join(ICI, sous)
        chemin = os.path.normpath(os.path.join(dossier, nom))
        if not chemin.startswith(dossier + os.sep) or not os.path.isfile(chemin):
            return self._json(404, {'erreur': 'introuvable'})
        ext = os.path.splitext(chemin)[1].lower()
        types = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                 '.json': 'application/json; charset=utf-8', '.css': 'text/css; charset=utf-8',
                 '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2'}
        with open(chemin, 'rb') as f:
            corps = f.read()
        self.send_response(200)
        self.send_header('Content-Type', types.get(ext, 'application/octet-stream'))
        self.send_header('Content-Length', str(len(corps)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(corps)

    def _page(self):
        try:
            with open(PAGE, 'rb') as f:
                corps = f.read()
        except OSError:
            return self._json(500, {'erreur': 'wrangle.html introuvable à côté de serveur.py'})
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(corps)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(corps)

    def _flux(self, q):
        client = (q.get('client') or [''])[0][:40]
        nom = (q.get('nom') or [''])[0]
        if not client:
            return self._json(400, {'erreur': 'client manquant'})
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Accel-Buffering', 'no')
        self.send_header('Connection', 'close')
        self.end_headers()

        abonne = {'q': queue.Queue(maxsize=500), 'client': client}
        with verrou:
            abonnes.append(abonne)
            noter_presence(client, nom=nom)
            premier = {'type': 'etat', 'db': etat['db'], 'rev': etat['rev'],
                       'adresses': self.server.adresses}
        print('+ %s (%s) — %d connecté(s)' % (nom or client, self.client_address[0], len(abonnes)))
        try:
            self.wfile.write(('retry: 2000\ndata: ' + json.dumps(premier, ensure_ascii=False) + '\n\n').encode('utf-8'))
            self.wfile.flush()
            diffuser(message_presence())
            while True:
                try:
                    brut = abonne['q'].get(timeout=20)
                except queue.Empty:
                    brut = ': battement\n\n'
                    noter_presence(client)
                self.wfile.write(brut.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with verrou:
                if abonne in abonnes:
                    abonnes.remove(abonne)
                encore = any(a['client'] == client for a in abonnes)
                if not encore:
                    presence.pop(client, None)
            print('- %s — %d connecté(s)' % (nom or client, len(abonnes)))
            diffuser(message_presence())

    # -- POST --------------------------------------------------------------

    def do_POST(self):
        u = urlparse(self.path)
        corps = self._lire_json()
        if corps is None:
            return self._json(400, {'erreur': 'JSON attendu'})

        if u.path == '/api/ops':
            client = str(corps.get('client') or '')[:40]
            ops = corps.get('ops')
            if not client or not isinstance(ops, list):
                return self._json(400, {'erreur': 'client et ops attendus'})
            with verrou:
                noter_presence(client, nom=corps.get('nom'))
                faites = appliquer(ops, client)
                rev = etat['rev']
            if faites:
                diffuser({'type': 'ops', 'client': client, 'rev': rev, 'ops': faites}, sauf=client)
                for op in faites:
                    if op['op'] == 'remplacer':
                        print('Projet remplacé par', corps.get('nom') or client,
                              '(%d plans, %d prises)' % (len(op['db']['plans']), len(op['db']['prises'])))
            # l'appareil émetteur reçoit ses opérations corrigées, sans le projet complet
            retour = [op if op['op'] != 'remplacer' else {'op': 'remplacer'} for op in faites]
            return self._json(200, {'rev': rev, 'ops': retour})

        if u.path == '/api/presence':
            client = str(corps.get('client') or '')[:40]
            if not client:
                return self._json(400, {'erreur': 'client attendu'})
            noter_presence(client, nom=corps.get('nom'), actif=corps.get('actif'))
            diffuser(message_presence())
            return self._json(200, {'ok': True})

        self._json(404, {'erreur': 'introuvable'})


# ------------------------------------------------------------------ Main ---

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    global DATA, FICHIER, SAUV
    port = 8765
    ouvrir = False
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == '--ouvrir':
            ouvrir = True
        elif a == '--data' and args:
            DATA = os.path.abspath(args.pop(0))
            FICHIER = os.path.join(DATA, 'projet.json')
            SAUV = os.path.join(DATA, 'sauvegardes')
        elif a.isdigit():
            port = int(a)

    os.makedirs(DATA, exist_ok=True)
    charger()
    sauvegarde_horodatee(force=True)   # état au démarrage, avant toute modification

    try:
        srv = ThreadingHTTPServer(('0.0.0.0', port), Requete)
    except OSError as e:
        print()
        print('Impossible d ouvrir le port %d : %s' % (port, e))
        print('Un serveur tourne sans doute deja. Ouvrez http://localhost:%d,' % port)
        print('ou lancez avec un autre port : py serveur.py %d' % (port + 1))
        return
    srv.daemon_threads = True
    srv.adresses = adresses_locales(port)

    print()
    print('=' * 62)
    print('  WRANGLE — serveur de plateau')
    print('=' * 62)
    print('  Sur cet ordinateur :   http://localhost:%d' % port)
    for a in srv.adresses:
        print('  Autres appareils :     ' + a)
    print()
    print('  Les téléphones et tablettes doivent être sur le même Wi-Fi.')
    print('  Données : ' + FICHIER)
    print('  Ctrl+C pour arrêter.')
    print('=' * 62)
    print()

    threading.Thread(target=boucle_entretien, daemon=True).start()
    if ouvrir:
        threading.Timer(0.8, lambda: webbrowser.open('http://localhost:%d' % port)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ecrire_maintenant()
        sauvegarde_horodatee(force=True)
        print('Serveur arrêté, projet enregistré.')


if __name__ == '__main__':
    main()
