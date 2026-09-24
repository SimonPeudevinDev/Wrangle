# Wrangle — journal de plateau

Un carnet de DIT / data wrangler : jours, séquences, plans, prises, cartes et rapport de fin de journée.
La page est `wrangle.html`, avec sa feuille de style et son logo dans `public/` : garder les deux ensemble.

## Comment ça marche

- **Un site, que chacun ouvre sur son téléphone**, où qu'il soit : en 4G, chez lui, sur le plateau.
  Pas de Wi-Fi commun, rien à installer. Sur iPhone / iPad : Safari > Partager > « Sur l'écran
  d'accueil » donne une icône plein écran.
- **On choisit son profil à l'entrée** (Romain, Simon, Tom…) ; la pastille en haut le rappelle. Le
  profil décide de ce qu'on voit : ses prises à soi, rien d'autre, tant qu'on ne change pas de profil
  (⚙ → Journée, ou l'écran d'entrée). Ses saisies sont rangées sur le serveur sous son prénom et le
  suivent sur tous ses appareils. Hors réseau, on continue à saisir, tout repart au retour (la
  pastille dit « hors ligne »).
- **Le DIT réunit tout d'un bouton** : Rapport → « Toute l'équipe ». La page va chercher les saisies
  de chacun sur le serveur et les réunit à celles d'ici : le bilan, le journal DIT (PDF), la fiche
  pour la post (PDF), la feuille de montage, l'ALE et le JSON portent alors sur l'ensemble, et les
  fichiers exportés s'appellent `…_equipe`. Le projet de cet appareil n'est pas modifié ;
  « Actualiser » va revoir ; « Mes saisies » revient à son propre bilan. Il n'y a pas de rôle DIT :
  c'est le bouton qui fait le DIT.
- **Le découpage est propre à chacun** : chaque profil part des plans de la production intégrés au
  site et garde sa copie (états, éléments captés, plans ajoutés). Quand deux personnes ont noté des
  choses différentes sur le même plan ou la même prise, Rapport → « Rapprocher les saisies » les met
  côte à côte, et « Garder la fusion comme projet » tranche.

Le serveur, c'est le site lui-même chez l'hébergeur (OVH, en PHP) : voir « Le site chez
l'hébergeur » plus bas. La liste des prénoms proposés à l'entrée est `EQUIPE`, en tête du script de
la page.

## Sur le plateau sans internet

Le même carnet marche aussi en réseau fermé, avec `serveur.py` sur un ordinateur du plateau.

1. Sur cet ordinateur, double-cliquer sur **`Lancer.bat`**. Une fenêtre noire s'ouvre et affiche les
   adresses ; la page s'ouvre dans le navigateur.
2. Sur chaque téléphone ou tablette, se connecter au **même Wi-Fi** et ouvrir dans le navigateur
   l'adresse affichée dans la fenêtre noire, par exemple `http://192.168.1.20:8765`. Cette adresse
   est aussi rappelée dans la page, ⚙ → « Équipe connectée ».

Même fonctionnement que sur le site : chacun son espace, le DIT réunit tout par « Toute l'équipe ».
Entre les appareils d'une même personne, chaque modification arrive en moins d'une seconde ; si deux
d'entre eux ajoutent une prise au même plan au même moment, le serveur attribue les numéros.

Laisser la fenêtre noire ouverte pendant le tournage. `Ctrl+C` ou fermer la fenêtre arrête le serveur
(les projets sont enregistrés avant l'arrêt).

## Où sont les données

- `data/espaces/<prénom>/projet.json` : le projet de chaque personne, réécrit à chaque modification
  (`nom.txt` à côté garde le prénom tel qu'elle l'écrit).
- `data/espaces/<prénom>/sauvegardes/` : une copie horodatée au démarrage puis toutes les 10 minutes
  dès qu'il y a du nouveau (60 dernières conservées). Pour revenir en arrière : arrêter le serveur,
  copier la sauvegarde voulue sur le `projet.json` de l'espace, relancer.
- Le projet du temps où le serveur n'avait qu'un carnet pour tout le monde (`data/projet.json`)
  déménage tout seul au premier démarrage dans l'espace `commun`, sauvegardes comprises : le DIT le
  retrouve dans le rapprochement, rien n'est perdu.
- Chaque appareil garde aussi une copie dans son navigateur : en cas de coupure Wi-Fi, on continue
  à saisir, et tout repart au retour du réseau (pastille « Hors ligne » en haut).
- Export JSON / CSV / ALE : bouton ⚙, section « Données » et « Exports pour la post ».

Le projet reste léger, et c'est voulu : chaque appareil le télécharge en entier à sa première
ouverture, parfois en 4G. Une prise pleinement remplie pèse 0,8 Ko, un plan 0,5 Ko. **Un croquis
n'est gardé que sous forme de traits** — environ 1 Ko — et l'aperçu de la fiche est redessiné à
l'ouverture au lieu d'être stocké en image. Seuls les plans de décor importés pèsent vraiment
(quelques centaines de Ko chacun, un par décor) : ils sont réduits à 1600 px et encodés dans le
plus léger du JPEG et du WebP. Comptez 2 à 3 Mo pour un tournage entier, sauvegardes non
comprises.

Première mise en route : quand un espace n'a encore rien reçu sur le serveur, le premier appareil de
cette personne y envoie son projet (les prises déjà saisies dans ce navigateur sous ce prénom
s'il y en a), et reçoit le découpage de l'équipe s'il en existe un. Un espace vidé exprès
(✕ Effacer, ou tous les plans retirés) reste un projet vide : les appareils qui le retrouvent
s'y rangent, ils ne renvoient pas leur ancienne copie.

## Travailler seul, sans serveur

Ouvrir directement `wrangle.html` dans un navigateur : la page travaille seule, données dans le
navigateur, comme avant. La pastille en haut indique « Local ».

## Le site chez l'hébergeur

C'est le serveur de tout le monde. Le site publié chez un hébergeur qui exécute PHP (OVH) fait
serveur lui-même : **chacun a son espace**, nommé d'après son prénom, et le DIT réunit tout par
Rapport → « Toute l'équipe ». Les scripts d'`api/` tiennent, par espace, le projet, le journal des
opérations et les sauvegardes, avec les mêmes appels et les mêmes réponses que `serveur.py` ; la
liste des connectés est commune. Les données vivent dans `api/donnees/espaces/<prénom>/`, interdit
au web.

**Le domaine et le serveur.** foresight-movie.com est rattaché à l'hébergement OVH (multisite,
zone DNS vers l'adresse de l'hébergement, certificat Let's Encrypt) : la page et le serveur sont
au même endroit, en https. Chacun, sur son téléphone et sa propre connexion, dépose ainsi ses
saisies dans son espace, et le DIT les retrouve toutes par « Toute l'équipe ». La copie publiée
sur GitHub Pages reste la page seule, sans serveur, à son adresse github.io. Si un jour une page
publiée ailleurs doit parler à ce serveur, `construire_site.py --api https://foresight-movie.com/api`
lui en donne l'adresse en tête ; les scripts PHP répondent aux autres origines.
La page sait qu'elle est chez l'hébergeur par une ligne en tête (`window.WRANGLE_SERVEUR='php'`,
posée par `construire_site.py --php`, ce que fait la publication pour la copie envoyée chez OVH)
et l'interroge toutes les deux secondes au lieu d'écouter un flux. Rien à installer ni à laisser
allumé. Dans chaque espace : le projet, le journal, une sauvegarde horodatée toutes les dix minutes
(60 gardées). Le journal DIT par mail
part par la fonction mail de l'hébergeur ; l'expéditeur se règle dans `api/donnees/mail.json`
(`{"expediteur": "journal@foresight-movie.com"}`). `py tests/verif_ovh.py` parle au site publié
pour vérifier que tout répond, dans deux espaces d'essai vidés à la fin (il faut le réseau).

Pas de mot de passe, c'est un choix : le site est privé, seule l'équipe en connaît l'adresse. Les
espaces séparent les saisies, ils ne les protègent pas — qui connaît l'adresse du site peut lire
ou écrire l'espace de n'importe quel prénom en ajoutant `?espace=…` à un appel. C'est le prix du
« on choisit son prénom, et c'est tout », et des saisies qui suivent la personne sur tous ses
appareils sans rien à recopier. Pour un tournage où cela ne suffirait pas, le serveur sur une
machine à soi, derrière HTTPS et un mot de passe, est la réponse (section suivante).

La page porte le numéro de la version publiée et le compare de loin en loin à `version.txt`, à
côté d'elle : un téléphone qui garde le site ouvert des jours propose alors de recharger. Chez
un hébergeur Apache, le `.htaccess` posé à la racine demande en plus que la page, la feuille de
style et les scripts soient revérifiés à chaque ouverture.

**Sur une machine à soi.** `serveur.py` posé sur un VPS fait la même chose, avec son flux en
direct. Deux précautions alors.

**Le mot de passe.** Sans lui, l'API obéit à n'importe qui, y compris pour remplacer le projet
entier. Dès que le serveur est joignable depuis internet :

```
py serveur.py --motdepasse "le-mot-de-passe-du-tournage"
```

ou la variable d'environnement `WRANGLE_MOTDEPASSE`. Chaque appareil le donne une fois et son
navigateur s'en souvient trois mois. Sans l'option, le serveur reste ouvert : c'est ce qu'on veut
sur le Wi-Fi d'un plateau, où tout le monde dans la pièce est de l'équipe. Changer le mot de
passe déconnecte tout le monde ; redémarrer le serveur, non.

**HTTPS.** Un mot de passe qui voyage en clair n'en est pas un. Mettre le serveur derrière un
reverse proxy qui s'occupe du certificat (Caddy, nginx). Il envoie l'en-tête `X-Forwarded-Proto`,
et le cookie d'accès cesse alors de voyager en clair.

**Sur un VPS.** Pour que tout le monde saisisse par internet, le serveur tourne sur une petite
machine louée (un VPS Ubuntu ou Debian). `outils/installer_vps.sh` fait tout : le dépôt dans
`/opt/wrangle`, `serveur.py` en service qui redémarre seul (données dans `/var/lib/wrangle`),
Caddy devant avec le certificat HTTPS automatique, le mot de passe du tournage. Il faut d'abord une
entrée DNS de type A qui mène le nom choisi (par exemple `plateau.foresight-movie.com`) à l'adresse
IP du VPS, puis, connecté en SSH au VPS :

```
curl -fsSL https://raw.githubusercontent.com/SimonPeudevinDev/Wrangle/main/outils/installer_vps.sh \
  | sudo bash -s -- plateau.foresight-movie.com "le-mot-de-passe-du-tournage"
```

Ensuite `sudo wrangle-maj` met à jour et relance. Le journal par mail y marche aussi : déposer
`mail.json` dans `/var/lib/wrangle/`.

## Rapprocher les saisies

« Toute l'équipe » réunit les saisies sans rien demander : les prises de chacun s'ajoutent, et quand
deux personnes ont rempli la même prise, celles d'ici font foi sur les écarts, les autres comblent
les vides. Pour voir ces écarts en détail, ou pour en faire son projet : « Rapprocher les saisies »,
juste en dessous dans le Rapport.

Sans serveur, chacun saisit de son côté, dans son navigateur, et personne ne voit les autres. Pour
tout réunir : chacun exporte sa sauvegarde (⚙ → Données → Sauvegarde JSON) et l'envoie au DIT, qui
la dépose dans Rapport → « Rapprocher les saisies ». Le rapport met les prises côte à côte, plan par
plan : un **écart** quand deux personnes ont écrit des valeurs différentes (statut, clip, carte,
timecodes, notes, réglages…), un **complément** quand une seule a rempli un champ, une **prise chez
un seul** quand une seule l'a saisie. « Garder la fusion comme projet » garde tout : les saisies de
ce navigateur font foi sur les écarts, les autres comblent les vides et apportent leurs prises en
plus. « Écarts (PDF) » sort le même rapport en PDF. Chaque fichier est nommé d'après qui a saisi ses
prises.

**Chacun ses saisies.** Partout, la copie locale du projet est rangée sous le prénom choisi à
l'entrée : passer de Simon à Romain sur le même téléphone (à l'entrée, ou ⚙ → Journée) change de
saisies, revenir les retrouve. Avec un serveur, l'appareil change en même temps d'espace dessus :
Romain retrouve ce qu'il a saisi sur ses autres appareils, et rien de ce que Simon a saisi.

**Le carnet d'avant.** Jusqu'à cette version, le site comme le serveur du plateau ne gardaient
qu'un carnet par navigateur, où tout le monde saisissait. Chaque prise y porte le prénom de qui
l'a saisie : ce carnet se partage donc, il ne se donne pas. Quand une personne se nomme, elle y
prend le découpage et ses prises à elle, et laisse celles des autres, qui les prendront à leur
tour ; quand il n'y reste plus de prise, il s'efface. Seules des prises sans nom laissent un
doute : la page demande alors, une fois par personne, et les laisse en place si on répond « pas
à moi ». Le serveur du plateau fait de même au premier démarrage avec `data/projet.json` : un
espace par auteur, les prises sans nom dans « commun », le fichier d'avant gardé en `.ancien` et
ses sauvegardes dans `data/sauvegardes-avant-espaces/`. Et si un carnet porte quand même des
prises saisies par d'autres, la page le voit et propose de les leur rendre : chaque prise repart
chez son auteur, ici et sur le serveur, et les siennes restent.

**Les prises sont à chacun, le découpage est à tous.** Un plan ajouté, modifié, déplacé ou
supprimé dans Préparation vaut pour toute l'équipe : le serveur reporte l'opération dans chaque
espace (un plan s'y reconnaît à sa séquence et son numéro). Un plan sur lequel quelqu'un a déjà
des prises ne lui est jamais retiré. La production et les optiques suivent la même règle. Un
nouveau venu reçoit le découpage de l'équipe, mêmes plans et mêmes identifiants, et garde ses
prises. « Recharger le découpage » (⚙ → Données) remet les plans dans l'ordre du DT, garde ce
qui a été saisi dessus, replie les doublons et laisse les plans ajoutés sur le plateau à la
suite ; comme c'est une opération sur le découpage, elle vaut pour tout le monde. Depuis la
fiche d'un plan ouverte en Tournage, on ne supprime pas de plan : c'est dans Préparation.

## Le journal DIT par mail

Le serveur peut envoyer le journal DIT en PDF, à la main (fiche Journée, « Envoyer maintenant »)
ou tout seul : toutes les heures ou toutes les deux heures, à l'heure pile, dans la plage réglée
au curseur ; ou une fois par jour à l'heure dite. Les envois automatiques ne courent qu'entre les
deux dates réglées (début et fin du tournage). Ces réglages sont dans la fiche Journée, partagés
par tous les appareils. Rien ne part si rien n'a changé depuis le dernier envoi.

La boîte d'envoi, elle, ne quitte pas l'ordinateur du serveur : copier `outils/mail.exemple.json`
en `data/mail.json` et y mettre le serveur SMTP, le port, la sécurité (`ssl`, `starttls` ou
`aucune`), l'identifiant, le mot de passe et l'expéditeur. Pour une boîte OVH : `ssl0.ovh.net`,
port 465, `ssl`. Le fichier est relu à chaque envoi, pas besoin de relancer.

À chaque créneau, chaque appareil ouvert tente l'envoi ; le serveur ne laisse passer que le premier.
Les envois sont notés dans `data/mails.json`.

## Trouver un plan

La barre des jours et des filtres suit la liste quand on descend : on change de jour sans remonter.

- **Les jours** : `Tout`, puis `J1`, `J2`… Chaque pastille donne les plans tournés sur les plans
  prévus (`7/18`), avec un trait d'avancement en pied. La journée bouclée passe au vert.
  Un point d'or marque le jour que l'on tourne — celui de la fiche ⚙ « Journée », ou à défaut
  le premier jour commencé. La pastille du jour affiché reste toujours en vue.
- **L'état du plan**, une seule réponse à la fois : `Tous`, `À tourner`, `Tournés`
  (`Abandonnés` n'apparaît que s'il y en a).
- **Les marqueurs**, à cumuler avec l'état et entre eux :
  - `À monter` : les plans qui ont une prise ★. La liste ne montre alors que ces prises-là.
  - `Éléments` : les plans qui portent des éléments VFX (HDRI, mire, textures…).
  - `À compléter` : les prises sans nom de clip ou sans carte, et les plans dits tournés sans
    aucune prise. C'est le ménage à faire avant de rendre la journée.
- **Saisie par** : dès que plusieurs personnes ont saisi, une rangée de prénoms apparaît — un
  bouton par personne trouvée dans les prises du jour affiché. Cliquer sur `Simon` ne garde que
  les plans où il a une prise et, dans ces plans, ne montre que les siennes. Un seul prénom à la
  fois ; recliquer dessus relâche le filtre. La rangée reste cachée tant qu'une seule personne
  a saisi : elle n'aurait rien à trier.
- Chaque bouton porte son compte pour le jour affiché : un filtre à `0` est éteint, on ne clique
  jamais vers une liste vide. **✕ Effacer** remet tout à zéro.

La page Tournage n'a pas de champ de recherche : on parcourt par jour et par filtre. La page
**Médias** garde le sien, pour retrouver une carte.

## Prises

- **● Moteur** (bouton flottant) : crée la prise sur le plan en cours, note l'heure et lance le chrono.
  Il devient **■ Coupez** : la durée est enregistrée. Le chrono est aussi accessible dans la fiche de la prise.
- **+ Prise** (petit bouton) ou « + Prise N » sous chaque plan : ajoute une prise sans chrono.
- Dans la liste : ★ (à monter), OK, NG sans ouvrir la fiche.
- Dans la fiche : résultat (OK, NG, Série, Faux départ, Pick-up), note libre et mots rapides
  (Raccord, Jeu, Cadre…), nom de clip avec suggestion du suivant (bouton ＋1), relevés caméra
  pour le matchmove, réglages image, son.
- Caméra, carte, optique, réglages : repris automatiquement de la prise précédente.
- Supprimer une prise, un plan ou une carte : « Annuler » dans le bandeau pendant 7 secondes.

## Divers

- ☼ / ☾ en haut : thème clair pour le plein soleil, sombre pour la nuit.
- La pastille en haut porte le prénom de qui saisit sur cet appareil ; son point dit l'état du
  réseau, et elle ajoute « hors ligne » ou « local » quand il n'y a pas de serveur au bout.
- Rapport → « Toute l'équipe » / « Mes saisies » : sur quoi portent le bilan et tous les exports.
- Le logo : `public/wrangle-logo.svg` (signe + mot), avec son original en image à côté.
  Le signe est aussi dans la page, en haut à gauche et en icône d'onglet. Il prend la couleur
  du thème : ses coutures sont des découpes, pas du blanc, donc il tient sur n'importe quel fond.
  `py vectoriser2.py sortie.svg source.png` le refabrique à partir d'une image. Il refuse
  d'écraser un logo dont le cadre ne correspond pas à la source : la page appelle le sien dans
  un cadre écrit en dur, un logo aux autres proportions y serait rogné sans prévenir.
- Rapport : filtrable par jour, alertes de cohérence (clips sans carte, cartes sans sauvegarde…),
  bouton Imprimer pour un PDF.

## Ce qu'on transmet à la post

Onglet **Rapport** → **Fiche pour la post (PDF)**. Elle reprend le jour choisi dans la rangée du
haut (`Tout` = tout le tournage) et se lit en trois temps :

1. **Pour le montage** : la liste des prises ★, dans l'ordre du tournage — clip, séquence, plan,
   durée, carte, note.
2. **Pour les VFX**, plan par plan : ce que le DT demandait, la prise qui
   fait foi avec son optique et ses réglages image, les **éléments captés** (HDRI, charte, boule
   chrome, fond vert…) et les **relevés matchmove** (point de map, hauteur, mesuré depuis, pan /
   tilt / roll). Les autres prises sont rappelées en une ligne, pour retrouver un plan B.
3. **Médias** : sur quelle carte sont les rushes, combien de copies, checksum vérifié ou non.

Les plans sans prise ni élément ne sont pas imprimés : la fiche ne contient que ce qui a été tourné.
Dans la fenêtre d'impression, choisir « Enregistrer au format PDF ».
- Port différent : `py serveur.py 9000`.

## Vérifier que rien n'est cassé

Dix-sept scripts pilotent un Chrome invisible sur un serveur et un dossier de données temporaires :
le projet réel n'est jamais touché.

```
py tests/lancer_scenario.py        deux appareils d'une même personne qui saisissent en même temps, et un troisième dans son espace
py tests/verif_espaces.py          chacun son espace sur le serveur, « Toute l'équipe » pour le DIT, et l'ancien projet commun repris
py tests/verif_rechargement.py     la page redémarre avec une copie locale déjà en place
py tests/verif_filtre_qui.py       le filtre « Saisie par »
py tests/verif_serveur_distant.py  le mode partagé hors du Wi-Fi du plateau
py tests/verif_croquis.py          le croquis, enregistré en traits et redessiné
py tests/verif_barre_jours.py      la rangée des jours, calée sur trois sur téléphone
py tests/verif_enchainement.py     les lignes de la fiche s'ouvrent l'une après l'autre
py tests/verif_reprise.py          recharger la page ramène là où on était
py tests/verif_dialogue.py         les boîtes de la page à la place de celles du navigateur
py tests/verif_journal_dit.py      le journal DIT en PDF : par jour, prises retenues, plans tournés, reste à tourner
py tests/verif_prep_cadrage.py     en préparation, plusieurs cadrages sur un plan
py tests/verif_viser.py            l'anneau des cartes choisit le plan que le Moteur va tourner
py tests/verif_mail.py             le journal DIT par mail, à la main et à l'heure dite
py tests/verif_rapprochement.py    rapprocher les saisies de plusieurs personnes, et les fusionner
py tests/verif_personnes.py         chacun ses saisies sur le site, et à qui revient le carnet d'avant
py tests/verif_interroger.py       la page en mode php, comme chez l'hébergeur : elle interroge au lieu d'écouter
```

Chacun prend son propre port. Si un script se plaint que le serveur est injoignable, c'est qu'un
serveur d'une précédente exécution occupe encore le port : le fermer avant de relancer.

Le décor est commun : `tests/banc.py` monte le serveur et le navigateur, puis les démonte et
efface ses dossiers temporaires. C'est là qu'on touche si les tests doivent changer de décor,
pas dans chaque script. À côté, `py tests/captures.py` prend une série de captures d'écran de
l'interface, en téléphone et en grand écran, pour la contrôler à l'œil.

## Publier le site

La page marche aussi toute seule sur Internet : données dans le navigateur de chacun, sans serveur
ni synchro. C'est ce qui est publié sur le nom de domaine.

`py outils/construire_site.py --vide` fabrique ce site dans `site/` : il reprend `wrangle.html`
sous le nom `index.html`, sans le découpage intégré (`window.DT_SEED`). C'est ce que publie le
workflow : le site s'ouvre sur un carnet vide, et la liste des plans se saisit dans Préparation
par une personne, pour toute l'équipe (voir « Les prises sont à chacun, le découpage est à
tous »). La page pèse 200 Ko au lieu de 1,4 Mo, et un garde-fou refuse de construire s'il
restait une trace des données. Le fichier du plateau n'est jamais touché.

Sans `--vide`, le site embarque le découpage du DT : tout le monde l'ouvre sur les plans du
tournage, et ⚙ > Données > « Recharger le découpage » remet les plans à jour sans toucher aux
prises.

Pour voir le résultat avant de publier : ouvrir `site/index.html` directement dans le navigateur.
(Par `http://localhost`, la page se croit sur un serveur de plateau et affiche « Hors ligne » :
c'est normal, `localhost` est une adresse locale.)

Publier : `git push`. GitHub relance la construction (`.github/workflows/publier.yml`) et, en une
minute, dépose le site chez OVH par FTP, dans le `www` de l'hébergement, puis met la copie sans
serveur sur GitHub Pages, à son adresse github.io. L'envoi chez OVH tient à trois secrets dans
GitHub (Settings > Secrets and variables > Actions) : `OVH_FTP_HOTE`
(`ftp.clusterNNN.hosting.ovh.net`), `OVH_FTP_UTILISATEUR` et `OVH_FTP_MOTDEPASSE` ; sans eux,
l'étape est sautée, et un envoi raté fait virer la publication au rouge.

Le nom de domaine, foresight-movie.com, est rattaché à l'hébergement dans l'espace client OVH :
l'hébergement > Mes sites > le domaine ajouté au site `www`, la zone DNS du domaine avec un
enregistrement A (et `www`) vers l'adresse IPv4 de l'hébergement, et un certificat Let's Encrypt
posé depuis l'onglet Certificats SSL. Le domaine n'est plus déclaré côté GitHub Pages : le
fichier `CNAME` a disparu du dépôt. Pour rattacher un autre domaine, même chemin.

Le mode partagé s'allume quand `serveur.py` sert la page : il la signe en tête
(`window.WRANGLE_SERVEUR`), où qu'il soit posé — Wi-Fi du plateau, nom de domaine, réseau privé.
Sans cette signature, la page juge sur l'adresse (`serveurPossible`) : `localhost`, IP privée, nom
en `.local` ou sans point. Le site publié n'a pas de serveur derrière et n'est pas signé : il reste
en mode local, chacun ses données dans son navigateur.
