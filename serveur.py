#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
WRANGLE — serveur de plateau.

Un seul fichier, bibliothèque standard uniquement (Python 3.8+).

  py serveur.py            démarre sur le port 8765
  py serveur.py 9000       autre port
  py serveur.py --ouvrir   démarre et ouvre le navigateur
  py serveur.py --motdepasse xxx   demande ce mot de passe à l'entrée
  py serveur.py --data D:\autre\dossier   range projet.json et les sauvegardes ailleurs
  py serveur.py --adresse 127.0.0.1       n'écoute qu'en local (derrière Caddy sur un VPS)

Le serveur :
  - sert la page wrangle.html et le dossier public/ (feuille de style, logo) ;
  - garde un espace par personne, nommé d'après son prénom
    (data/espaces/<prénom>/projet.json) : chacun ne voit que ses saisies, sur
    tous ses appareils ; le DIT réunit celles de tous dans le rapprochement
    (GET /api/espaces puis /api/etat?espace=…) ;
  - reçoit les modifications de chaque appareil (POST /api/ops) sous forme
    d'opérations champ par champ, les applique à l'espace et les rediffuse
    aux appareils branchés sur cet espace par flux SSE (GET /api/flux) ;
  - tient la liste des personnes connectées, tous espaces confondus ;
  - fait une sauvegarde horodatée dans chaque espace toutes les 10 min dès
    que quelque chose y a changé (60 dernières conservées).

Le projet du temps où le serveur n'avait qu'un carnet (data/projet.json)
devient l'espace « commun » au premier démarrage : le DIT le retrouve dans
le rapprochement, rien n'est perdu.

Tous les appareils doivent être sur le même réseau (Wi-Fi du plateau) et
ouvrir l'adresse affichée au démarrage.
"""

import base64
import hashlib
import hmac
import json
import os
import queue
import re
import socket
import sys
import threading
import time
import unicodedata
import webbrowser
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ICI, 'wrangle.html')


def ranger_donnees(dossier):
    """Où vivent les espaces (un dossier par prénom : projet, sauvegardes) et
    la boîte mail. `--data` déplace tout d'un coup."""
    global DATA, ESPACES
    DATA = os.path.abspath(dossier)
    ESPACES = os.path.join(DATA, 'espaces')


DATA = ESPACES = ''
ranger_donnees(os.path.join(ICI, 'data'))

SAUV_TOUTES_LES = 10 * 60      # secondes entre deux sauvegardes horodatées
SAUV_CONSERVEES = 60
PRESENCE_EXPIRE = 90           # secondes sans nouvelle d'un client avant retrait
COOKIE = 'wrangle_acces'       # le laissez-passer gardé par le navigateur
COOKIE_DUREE = 90 * 24 * 3600  # un tournage entier sans redemander le mot de passe

COLLECTIONS = {'plan': 'plans', 'prise': 'prises'}

HTML = 'text/html; charset=utf-8'
TYPES = {'.html': HTML, '.js': 'text/javascript; charset=utf-8',
         '.json': 'application/json; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml',
         '.webp': 'image/webp', '.woff2': 'font/woff2'}

# ----------------------------------------------------------------- État ---

verrou = threading.RLock()
espaces = {}          # slug -> espace : {'slug', 'db', 'rev', 'journal', 'nom', 'sale', 'derniere_sauv', 'quand', 't_ecriture'}
abonnes = []          # files SSE : {'q': Queue, 'client': id, 'espace': slug}
presence = {}         # client -> {'nom', 'actif', 'espace', 'vu'}


def collection(db, kind):
    """La liste qui porte ce genre de fiche ('plan' -> db['plans']), ou None."""
    return db.get(COLLECTIONS[kind]) if db and kind in COLLECTIONS else None


def place_apres(coll, apres):
    """Où insérer un plan : juste après celui dont c'est l'identifiant, en tête
    si `apres` est vide, à la fin si on ne le trouve pas."""
    if not apres:
        return 0
    for i, p in enumerate(coll):
        if p.get('id') == apres:
            return i + 1
    return len(coll)


def ecrire_json(chemin, db):
    """Le projet dans ce fichier, au format compact."""
    with open(chemin, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))


# ------------------------------------------------------------------ Mail ---
# Le journal DIT part par mail : la page fabrique le PDF, le serveur l'expédie
# avec la boîte réglée dans data/mail.json (voir LISEZMOI). Les identifiants
# ne quittent pas cet ordinateur.

envois_en_cours = set()   # les envois automatiques en train de partir : un seul par journée


def config_mail():
    """La boîte d'envoi, relue à chaque envoi : on la corrige sans relancer."""
    chemin = os.path.join(DATA, 'mail.json')
    if not os.path.exists(chemin):
        return None
    try:
        with open(chemin, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return cfg if cfg.get('smtp') and cfg.get('expediteur') else None
    except Exception as e:
        print('data/mail.json illisible :', e)
        return None


def envois_mail():
    """Le journal des envois, les deux cents derniers."""
    try:
        with open(os.path.join(DATA, 'mails.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def noter_envoi(entree):
    ecrire_json(os.path.join(DATA, 'mails.json'), (envois_mail() + [entree])[-200:])


def expedier(cfg, destinataires, sujet, texte, nom, pdf):
    """Un mail avec le PDF en pièce jointe, par la boîte configurée."""
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg['From'] = cfg['expediteur']
    msg['To'] = ', '.join(destinataires)
    msg['Subject'] = sujet
    msg.set_content(texte)
    msg.add_attachment(pdf, maintype='application', subtype='pdf', filename=nom)
    hote, port = cfg['smtp'], int(cfg.get('port') or 465)
    securite = (cfg.get('securite') or 'ssl').lower()
    if securite == 'ssl':
        srv = smtplib.SMTP_SSL(hote, port, timeout=30)
    else:
        srv = smtplib.SMTP(hote, port, timeout=30)
        if securite == 'starttls':
            srv.starttls()
    try:
        if cfg.get('utilisateur'):
            srv.login(cfg['utilisateur'], cfg.get('motdepasse') or '')
        srv.send_message(msg)
    finally:
        try:
            srv.quit()
        except Exception:
            pass


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


# ---------------------------------------------------------------- Espaces ---
# Un espace par personne, nommé d'après son prénom (« marie-lou ») : son
# projet, son journal des opérations, ses sauvegardes. Un appareil qui ne dit
# pas d'espace tombe dans « commun ». Mêmes noms et mêmes réponses que les
# scripts d'api/ chez l'hébergeur.

def slug(s):
    """« Noémie » -> noemie : le nom du dossier d'une personne, sans accent ni
    majuscule, comme la page le calcule (espaceDe) et comme le fait api/."""
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9-]+', '-', s.lower()).strip('-')[:40]


def espace_neuf(nom):
    return {'slug': nom, 'db': None, 'rev': 0, 'journal': [], 'nom': '', 'sale': False,
            'derniere_sauv': 0.0, 'quand': 0.0, 't_ecriture': None}


def espace_etat(nom):
    """L'espace de ce prénom (déjà en slug ou non), créé au premier appel ;
    « commun » quand l'appareil n'en dit pas."""
    s = slug(nom) or 'commun'
    with verrou:
        e = espaces.get(s)
        if e is None:
            e = espaces[s] = espace_neuf(s)
        return e


def dossier_espace(e):
    return os.path.join(ESPACES, e['slug'])


def fichier_espace(e):
    return os.path.join(dossier_espace(e), 'projet.json')


def noter_nom(e, nom):
    """Le prénom tel que la personne l'écrit, pour la liste des espaces."""
    nom = str(nom or '').strip()[:40]
    if not nom or e['nom'] == nom or e['slug'] == 'commun':   # « commun » n'est a personne
        return
    e['nom'] = nom
    try:
        os.makedirs(dossier_espace(e), exist_ok=True)
        with open(os.path.join(dossier_espace(e), 'nom.txt'), 'w', encoding='utf-8') as f:
            f.write(nom)
    except OSError:
        pass


def liste_espaces():
    """Les espaces qui ont un projet, pour le rapprochement du DIT."""
    with verrou:
        liste = [{'espace': k, 'nom': e['nom'] or ('Commun' if k == 'commun' else k), 'rev': e['rev'],
                  'plans': len(e['db']['plans']), 'prises': len(e['db']['prises']),
                  'quand': datetime.fromtimestamp(e['quand'] or time.time()).isoformat(timespec='seconds')}
                 for k, e in espaces.items() if e['db'] and e['db']['plans']]
    return sorted(liste, key=lambda x: x['nom'].lower())


def reprendre_ancien_projet():
    """Le projet du temps où le serveur n'avait qu'un carnet (data/projet.json)
    se partage entre ses auteurs : chaque prise porte le prénom de qui l'a
    saisie, et chacun reçoit dans son espace le découpage et ses prises à lui.
    Les prises sans nom vont dans l'espace « commun ». Le fichier d'avant reste
    à côté, en .ancien, et ses sauvegardes dans sauvegardes-avant-espaces/."""
    vieux = os.path.join(DATA, 'projet.json')
    if not os.path.exists(vieux):
        return
    try:
        with open(vieux, 'r', encoding='utf-8') as f:
            db = normaliser(json.load(f))
    except Exception as e:
        os.replace(vieux, vieux + '.illisible')
        print('Le projet d avant les espaces est illisible, mis de côté :', e)
        return
    parts = {}                     # slug -> (prénom tel qu'écrit, prises)
    for t in db['prises']:
        nom = str((t.get('par') if isinstance(t, dict) else '') or '').strip()
        parts.setdefault(slug(nom) or 'commun', (nom, []))[1].append(t)
    if not parts:
        parts['commun'] = ('', [])  # rien que le découpage : il attend dans « commun »
    for s, (nom, prises) in parts.items():
        d = os.path.join(ESPACES, s)
        f = os.path.join(d, 'projet.json')
        if os.path.exists(f):
            print('Espace %s : déjà là, les %d prise(s) du projet d avant restent dans projet.json.ancien' % (nom or s, len(prises)))
            continue
        os.makedirs(d, exist_ok=True)
        part = dict(db)
        part['prises'] = prises
        ecrire_json(f, part)
        if nom and s != 'commun':
            with open(os.path.join(d, 'nom.txt'), 'w', encoding='utf-8') as fh:
                fh.write(nom[:40])
        print('Espace %s : le découpage et %d prise(s) du projet d avant' % (nom or s, len(prises)))
    os.replace(vieux, vieux + '.ancien')
    anciennes = os.path.join(DATA, 'sauvegardes')
    if os.path.isdir(anciennes) and not os.path.exists(anciennes + '-avant-espaces'):
        os.replace(anciennes, anciennes + '-avant-espaces')


def charger():
    """Tous les espaces enregistrés sur le disque."""
    os.makedirs(ESPACES, exist_ok=True)
    reprendre_ancien_projet()
    for s in sorted(os.listdir(ESPACES)):
        f = os.path.join(ESPACES, s, 'projet.json')
        if not os.path.isfile(f):
            continue
        e = espace_etat(s)
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                e['db'] = normaliser(json.load(fh))
            e['quand'] = os.path.getmtime(f)
            try:
                with open(os.path.join(ESPACES, s, 'nom.txt'), 'r', encoding='utf-8') as fh:
                    e['nom'] = fh.read().strip()[:40]
            except OSError:
                pass
            print('Espace %s : %d plans, %d prises' % (e['nom'] or s, len(e['db']['plans']), len(e['db']['prises'])))
        except Exception as ex:  # fichier abîmé : on le met de côté, on ne l'écrase pas
            cote = f + '.illisible-' + datetime.now().strftime('%Y%m%d-%H%M%S')
            os.replace(f, cote)
            print('Projet illisible, mis de côté :', cote, '(', ex, ')')
    if not any(e['db'] for e in espaces.values()):
        print('Aucun projet enregistré : chaque appareil enverra le sien à sa première connexion.')


def ecrire_maintenant(e):
    """Écriture atomique du projet de l'espace : fichier temporaire puis remplacement."""
    with verrou:
        e['t_ecriture'] = None
        if e['db'] is None:
            return
        os.makedirs(dossier_espace(e), exist_ok=True)
        tmp = fichier_espace(e) + '.tmp'
        ecrire_json(tmp, e['db'])
        os.replace(tmp, fichier_espace(e))
        e['sale'] = True


def planifier_ecriture(e):
    with verrou:
        if e['t_ecriture'] is None:
            e['t_ecriture'] = threading.Timer(0.4, ecrire_maintenant, args=(e,))
            e['t_ecriture'].daemon = True
            e['t_ecriture'].start()


def sauvegarde_horodatee(e, force=False):
    with verrou:
        if e['db'] is None or (not e['sale'] and not force):
            return
        sauv = os.path.join(dossier_espace(e), 'sauvegardes')
        os.makedirs(sauv, exist_ok=True)
        nom = os.path.join(sauv, 'projet_' + datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.json')
        ecrire_json(nom, e['db'])
        e['sale'] = False
        e['derniere_sauv'] = time.time()
        anciennes = sorted(x for x in os.listdir(sauv) if x.startswith('projet_') and x.endswith('.json'))
        for x in anciennes[:-SAUV_CONSERVEES]:
            try:
                os.remove(os.path.join(sauv, x))
            except OSError:
                pass


def tous_les_espaces():
    with verrou:
        return list(espaces.values())


def boucle_entretien():
    """Sauvegardes horodatées et nettoyage des présences fantômes."""
    while True:
        time.sleep(15)
        try:
            for e in tous_les_espaces():
                if time.time() - e['derniere_sauv'] >= SAUV_TOUTES_LES:
                    sauvegarde_horodatee(e)
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
    coll = collection(db, kind)
    if coll is None or not id_:
        return None
    for e in coll:
        if isinstance(e, dict) and e.get('id') == id_:
            return e
    return None


def appliquer(ops, client, esp):
    """Applique les opérations d'un appareil au projet de l'espace `esp`.
    Retourne les opérations effectivement réalisées (parfois corrigées ou
    complétées)."""
    sortie = []
    db = esp['db']
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
            esp['db'] = db = normaliser(d)
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
            coll = collection(db, kind)
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
            if kind == 'plan' and apres is not None:
                coll.insert(place_apres(coll, apres), data)
            else:
                coll.append(data)
            res = {'op': 'add', 'kind': kind, 'data': data}
            if kind == 'plan' and apres is not None:
                res['apres'] = apres
            sortie.append(res)

        elif t == 'del':
            id_ = op.get('id')
            coll = collection(db, kind)
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
            coll.insert(place_apres(coll, apres), bouge[0])
            sortie.append({'op': 'move', 'kind': 'plan', 'id': id_, 'apres': apres})

        elif t == 'optiques':
            liste = op.get('liste')
            if isinstance(liste, list):
                db['optiques'] = [str(x) for x in liste]
                sortie.append({'op': 'optiques', 'liste': db['optiques']})

    if sortie:
        esp['rev'] += 1
        esp['quand'] = time.time()
        noter_journal(esp, esp['rev'], client, sortie)
        planifier_ecriture(esp)
    return sortie


# ----------------------------------------------------------------- Journal ---
# Les dernières opérations de l'espace, pour les appareils qui interrogent le
# serveur au lieu d'écouter son flux (la page en mode « php », comme chez
# l'hébergeur : mêmes réponses qu'api/depuis.php, ce qui permet de tester ce
# mode ici).

JOURNAL_GARDE = 400


def noter_journal(e, rev, client, faites):
    e['journal'].append({'rev': rev, 'client': client,
                         'ops': [op if op['op'] != 'remplacer' else {'op': 'remplacer'} for op in faites]})
    del e['journal'][:-JOURNAL_GARDE]


def journal_depuis(e, rev):
    """Les entrées après rev, ou None s'il faut le projet entier (trop de
    retard, ou un remplacement entre-temps)."""
    entrees, attendu = [], rev + 1
    for x in e['journal']:
        if x['rev'] <= rev:
            continue
        if x['rev'] != attendu or any(op['op'] == 'remplacer' for op in x['ops']):
            return None
        entrees.append(x)
        attendu += 1
    return entrees


# --------------------------------------------------------------- Diffusion ---

def diffuser(message, espace=None, sauf=None):
    """Aux appareils branchés sur cet espace (tous, si aucun n'est dit :
    la présence est commune)."""
    brut = 'data: ' + json.dumps(message, ensure_ascii=False) + '\n\n'
    with verrou:
        cibles = list(abonnes)
    for a in cibles:
        if sauf is not None and a['client'] == sauf:
            continue
        if espace is not None and a['espace'] != espace:
            continue
        try:
            a['q'].put_nowait(brut)
        except queue.Full:
            pass


def message_presence():
    with verrou:
        liste = [{'client': c, 'nom': p.get('nom', ''), 'actif': p.get('actif', ''), 'espace': p.get('espace', '')}
                 for c, p in presence.items()]
    return {'type': 'presence', 'liste': liste}


def noter_presence(client, nom=None, actif=None, espace=None):
    if not client:
        return
    with verrou:
        p = presence.setdefault(client, {'nom': '', 'actif': '', 'espace': '', 'vu': 0})
        if nom is not None:
            p['nom'] = str(nom)[:40]
        if actif is not None:
            p['actif'] = str(actif)[:80]
        if espace is not None:
            p['espace'] = espace
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

# ---------------------------------------------------------------- Accès ---

# Vide, le serveur est ouvert : c'est ce qu'on veut sur le Wi-Fi d'un plateau,
# où tout le monde dans la pièce est de l'équipe. Renseigné (--motdepasse, ou
# la variable WRANGLE_MOTDEPASSE), chaque appareil le donne une fois et son
# navigateur s'en souvient. Indispensable dès que le serveur est joignable
# depuis internet : sans lui l'API obéit à tout le monde, y compris pour un
# remplacement complet du projet.
MOT_DE_PASSE = os.environ.get('WRANGLE_MOTDEPASSE', '')

ENTREE = """<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Wrangle</title>
<style>
  :root{ color-scheme:dark }
  *{ box-sizing:border-box }
  body{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px;
        background:#101114; color:#e8e8ea;
        font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif }
  form{ width:100%; max-width:320px }
  h1{ margin:0 0 2px; font-size:23px; letter-spacing:.02em }
  .sous{ margin:0 0 26px; color:#8b8d94; font-size:14px }
  label{ display:block; margin-bottom:8px; font-size:13px; color:#8b8d94 }
  input{ width:100%; padding:13px 14px; border-radius:10px; border:1px solid #2a2c33;
         background:#17181d; color:inherit; font-size:17px }
  input:focus{ outline:none; border-color:#4b8bf5 }
  button{ width:100%; margin-top:14px; padding:13px; border:0; border-radius:10px;
          background:#4b8bf5; color:#fff; font-size:16px; font-weight:600 }
  .rate{ margin-top:16px; padding:10px 12px; border-radius:8px;
         background:#3a1d1f; color:#ff9d9d; font-size:14px }
</style>
</head><body>
<form method="post" action="/entrer">
  <h1>Wrangle</h1>
  <p class="sous">Journal de plateau</p>
  <label for="mdp">Mot de passe du tournage</label>
  <input id="mdp" name="mdp" type="password" autocomplete="current-password" autofocus>
  <button type="submit">Entrer</button>
  <!--avis-->
</form>
</body></html>
"""


def laissez_passer(mdp):
    """Le jeton déposé dans le navigateur. Il découle du mot de passe seul :
    redémarrer le serveur ne déconnecte personne, changer le mot de passe
    déconnecte tout le monde."""
    return hashlib.sha256(('wrangle:' + mdp).encode('utf-8')).hexdigest()


def pareils(a, b):
    """Comparaison à durée constante, accents compris."""
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


class Requete(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'FSTDW/2'

    def log_message(self, fmt, *args):
        pass    # silence : le journal ne montre que les événements utiles

    # -- utilitaires -------------------------------------------------------

    def _repondre(self, code, corps=b'', type_=None, entetes=(), cors=False):
        """Toute réponse passe par ici : le code, les en-têtes, le corps.
        Rien n'est mis en cache — sur le plateau, la page doit être la bonne."""
        self.send_response(code)
        if type_:
            self.send_header('Content-Type', type_)
        self.send_header('Content-Length', str(len(corps)))
        self.send_header('Cache-Control', 'no-store')
        for nom, valeur in entetes:
            self.send_header(nom, valeur)
        if cors:
            self._cors()
        self.end_headers()
        if corps:
            self.wfile.write(corps)

    def _json(self, code, obj):
        self._repondre(code, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                       TYPES['.json'], cors=True)

    def _cors(self):
        # la page ouverte en fichier local (file://) peut envoyer son projet au serveur
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def do_OPTIONS(self):
        self._repondre(204, cors=True)

    def _lire_json(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > 64 * 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception:
            return None

    # -- entrée ------------------------------------------------------------

    def _entre(self):
        """Cet appareil a-t-il déjà donné le mot de passe ?"""
        if not MOT_DE_PASSE:
            return True
        try:
            biscuit = SimpleCookie(self.headers.get('Cookie') or '').get(COOKIE)
        except Exception:
            return False
        return biscuit is not None and pareils(biscuit.value,
                                               laissez_passer(MOT_DE_PASSE))

    def _refuse(self, u):
        """Une page renvoie au formulaire ; l'API répond 401, et la page en
        conclut qu'elle a perdu le fil, comme lors d'une coupure réseau."""
        if u.path.startswith('/api/'):
            return self._json(401, {'erreur': 'mot de passe attendu'})
        self._page_entree()

    def _page_entree(self, rate=False):
        avis = '<div class="rate">Mot de passe incorrect.</div>' if rate else ''
        self._repondre(401 if rate else 200,
                       ENTREE.replace('<!--avis-->', avis).encode('utf-8'), HTML)

    def _connexion(self):
        """Le formulaire : on vérifie, puis on dépose le laissez-passer."""
        n = int(self.headers.get('Content-Length') or 0)
        brut = self.rfile.read(n).decode('utf-8', 'replace') if 0 < n <= 4096 else ''
        donne = (parse_qs(brut).get('mdp') or [''])[0]
        if not MOT_DE_PASSE or not pareils(donne, MOT_DE_PASSE):
            print('Mot de passe refusé depuis', self.client_address[0])
            return self._page_entree(rate=True)
        # derrière un reverse proxy en HTTPS, le cookie ne doit plus voyager en clair
        sur = (self.headers.get('X-Forwarded-Proto') or '').lower() == 'https'
        biscuit = '%s=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Lax%s' % (
            COOKIE, laissez_passer(MOT_DE_PASSE), COOKIE_DUREE, '; Secure' if sur else '')
        self._repondre(303, entetes=[('Location', '/'), ('Set-Cookie', biscuit)])

    # -- GET ---------------------------------------------------------------

    def _url(self):
        """L'adresse demandée. « api/etat.php » vaut « /api/etat » : la page
        en mode php (celle du site chez l'hébergeur) se teste sur ce serveur."""
        u = urlparse(self.path)
        return u._replace(path=re.sub(r'^/api/(\w+)\.php$', r'/api/\1', u.path))

    def do_GET(self):
        u = self._url()
        if u.path == '/entrer':
            return self._page_entree()
        if not self._entre():
            return self._refuse(u)
        if u.path in ('/', '/index.html', '/wrangle.html'):
            return self._page()
        if u.path == '/api/etat':
            e = espace_etat((parse_qs(u.query).get('espace') or [''])[0])
            with verrou:
                return self._json(200, {'db': e['db'], 'rev': e['rev'],
                                        'presence': message_presence()['liste'],
                                        'adresses': self.server.adresses})
        if u.path == '/api/depuis':
            return self._depuis(parse_qs(u.query))
        if u.path == '/api/espaces':
            with verrou:
                return self._json(200, {'espaces': liste_espaces()})
        if u.path == '/api/flux':
            return self._flux(parse_qs(u.query))
        if u.path == '/api/mail':
            cfg = config_mail()
            return self._json(200, {'possible': bool(cfg), 'expediteur': (cfg or {}).get('expediteur', ''),
                                    'envois': envois_mail()[-10:]})
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
        with open(chemin, 'rb') as f:
            corps = f.read()
        ext = os.path.splitext(chemin)[1].lower()
        self._repondre(200, corps, TYPES.get(ext, 'application/octet-stream'))

    def _page(self):
        try:
            with open(PAGE, 'rb') as f:
                corps = f.read()
        except OSError:
            return self._json(500, {'erreur': 'wrangle.html introuvable à côté de serveur.py'})
        # La page ne peut pas deviner qu'un serveur la sert : derrière un nom de
        # domaine ou une IP de réseau privé, elle se croirait sur le site publié
        # et resterait en mode local. On le lui dit donc en clair.
        corps = corps.replace(b'<head>',
                              b'<head><script>window.WRANGLE_SERVEUR=1</script>', 1)
        self._repondre(200, corps, HTML)

    def _depuis(self, q):
        """Ce qui a changé depuis une révision, pour un appareil qui interroge
        au lieu d'écouter : les opérations du journal, ou le projet entier
        (première fois, trop de retard, remplacement entre-temps)."""
        try:
            rev = int((q.get('rev') or ['0'])[0] or 0)
        except ValueError:
            rev = 0
        client = (q.get('client') or [''])[0][:40]
        nom = (q.get('nom') or [None])[0]
        e = espace_etat((q.get('espace') or [''])[0])
        with verrou:
            actuel = e['rev']
            rep = {'rev': actuel}
            if rev <= 0 or rev > actuel:
                rep['db'] = e['db']
            elif rev < actuel:
                entrees = journal_depuis(e, rev)
                if entrees is None:
                    rep['db'] = e['db']
                else:
                    rep['ops'] = entrees
            if client:
                noter_presence(client, nom=nom, espace=e['slug'])
            noter_nom(e, nom)
            rep['presence'] = message_presence()['liste']
        return self._json(200, rep)

    def _flux(self, q):
        client = (q.get('client') or [''])[0][:40]
        nom = (q.get('nom') or [''])[0]
        if not client:
            return self._json(400, {'erreur': 'client manquant'})
        e = espace_etat((q.get('espace') or [''])[0])
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Accel-Buffering', 'no')
        self.send_header('Connection', 'close')
        self.end_headers()

        abonne = {'q': queue.Queue(maxsize=500), 'client': client, 'espace': e['slug']}
        with verrou:
            abonnes.append(abonne)
            noter_presence(client, nom=nom, espace=e['slug'])
            noter_nom(e, nom)
            premier = {'type': 'etat', 'db': e['db'], 'rev': e['rev'],
                       'adresses': self.server.adresses}
        print('+ %s (%s, espace %s) — %d connecté(s)' % (nom or client, self.client_address[0], e['slug'], len(abonnes)))
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
        u = self._url()
        if u.path == '/entrer':
            return self._connexion()
        if not self._entre():
            return self._refuse(u)
        corps = self._lire_json()
        if corps is None:
            return self._json(400, {'erreur': 'JSON attendu'})

        if u.path == '/api/ops':
            client = str(corps.get('client') or '')[:40]
            ops = corps.get('ops')
            if not client or not isinstance(ops, list):
                return self._json(400, {'erreur': 'client et ops attendus'})
            e = espace_etat(corps.get('espace') or '')
            with verrou:
                noter_presence(client, nom=corps.get('nom'), espace=e['slug'])
                noter_nom(e, corps.get('nom'))
                faites = appliquer(ops, client, e)
                rev = e['rev']
            if faites:
                diffuser({'type': 'ops', 'client': client, 'rev': rev, 'ops': faites}, espace=e['slug'], sauf=client)
                for op in faites:
                    if op['op'] == 'remplacer':
                        print('Projet de l espace %s remplacé par %s (%d plans, %d prises)' % (
                            e['slug'], corps.get('nom') or client, len(op['db']['plans']), len(op['db']['prises'])))
            # l'appareil émetteur reçoit ses opérations corrigées, sans le projet complet
            retour = [op if op['op'] != 'remplacer' else {'op': 'remplacer'} for op in faites]
            return self._json(200, {'rev': rev, 'ops': retour})

        if u.path == '/api/presence':
            client = str(corps.get('client') or '')[:40]
            if not client:
                return self._json(400, {'erreur': 'client attendu'})
            noter_presence(client, nom=corps.get('nom'), actif=corps.get('actif'),
                           espace=slug(corps.get('espace') or '') or 'commun')
            diffuser(message_presence())
            return self._json(200, {'ok': True})

        if u.path == '/api/mail':
            return self._mail(corps)

        self._json(404, {'erreur': 'introuvable'})

    def _mail(self, corps):
        """Expédie le journal DIT que la page a fabriqué. Un envoi automatique
        ne part qu'une fois par créneau, quel que soit le nombre d'appareils
        qui le tentent à la même minute."""
        cfg = config_mail()
        if not cfg:
            return self._json(503, {'erreur': "aucune boîte d'envoi : data/mail.json manque ou est incomplet"})
        a = [str(x).strip() for x in (corps.get('destinataires') or []) if str(x).strip()]
        if not a:
            return self._json(400, {'erreur': 'destinataires attendus'})
        try:
            pdf = base64.b64decode(corps.get('pdf') or '')
        except Exception:
            pdf = b''
        if not pdf.startswith(b'%PDF'):
            return self._json(400, {'erreur': 'PDF attendu'})
        auto = bool(corps.get('auto'))
        cle = str(corps.get('creneau') or '')[:60]    # « 2026-09-23 J1 14h » : un envoi par créneau
        with verrou:
            if auto and cle and (cle in envois_en_cours or any(e.get('auto') and e.get('cle') == cle for e in envois_mail())):
                return self._json(200, {'ok': False, 'deja': True})
            if auto and cle:
                envois_en_cours.add(cle)
        try:
            expedier(cfg, a, str(corps.get('sujet') or 'Journal DIT'), str(corps.get('texte') or ''),
                     str(corps.get('nom') or 'journal-DIT.pdf'), pdf)
        except Exception as e:
            with verrou:
                envois_en_cours.discard(cle)
            print('Envoi du journal refusé :', e)
            return self._json(502, {'erreur': str(e)})
        entree = {'quand': datetime.now().strftime('%Y-%m-%d %H:%M'), 'cle': cle, 'jour': corps.get('jour') or '',
                  'a': a, 'auto': auto, 'par': str(corps.get('nomClient') or '')[:40], 'octets': len(pdf)}
        with verrou:
            noter_envoi(entree)
            envois_en_cours.discard(cle)
        print('Journal DIT envoyé à', ', '.join(a), '(%d Ko)' % (len(pdf) // 1024))
        return self._json(200, {'ok': True, 'a': a, 'quand': entree['quand']})


# ------------------------------------------------------------------ Main ---

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    global MOT_DE_PASSE
    port = 8765
    adresse = '0.0.0.0'
    ouvrir = False
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == '--ouvrir':
            ouvrir = True
        elif a == '--motdepasse' and args:
            MOT_DE_PASSE = args.pop(0)
        elif a == '--data' and args:
            ranger_donnees(args.pop(0))
        elif a == '--adresse' and args:
            adresse = args.pop(0)
        elif a.isdigit():
            port = int(a)

    os.makedirs(DATA, exist_ok=True)
    charger()
    for e in tous_les_espaces():
        sauvegarde_horodatee(e, force=True)   # état au démarrage, avant toute modification

    try:
        srv = ThreadingHTTPServer((adresse, port), Requete)
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
    if MOT_DE_PASSE:
        print('  Accès : mot de passe demandé une fois par appareil.')
    print('  Données : un dossier par prénom dans ' + ESPACES)
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
        for e in tous_les_espaces():
            ecrire_maintenant(e)
            sauvegarde_horodatee(e, force=True)
        print('Serveur arrêté, projets enregistrés.')


if __name__ == '__main__':
    main()
