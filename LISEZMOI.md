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
  pastille dit « hors ligne ») — même si l'appli a été fermée entre-temps : ce qui n'est pas
  parti est gardé sur le téléphone et envoyé à la réouverture.
- **Le DIT réunit tout d'un bouton** : Rapport → « Toute l'équipe ». La page va chercher les saisies
  de chacun sur le serveur et les réunit à celles d'ici : le bilan, le journal DIT (PDF), la fiche
  pour la post (PDF), la feuille de montage, l'ALE et le JSON portent alors sur l'ensemble, et les
  fichiers exportés s'appellent `…_equipe`. Le projet de cet appareil n'est pas modifié ;
  « Actualiser » va revoir ; « Mes saisies » revient à son propre bilan. Il n'y a pas de rôle DIT :
  c'est le bouton qui fait le DIT.
- **Qui réunir** : sous « Rapprocher les saisies », chaque personne présente sur le serveur a sa
  pastille, avec son nombre de prises ; on coche une personne, plusieurs, ou « Tous ». « Tous », ce
  sont ceux qui ont saisi au moins une prise : un prénom choisi un jour sans rien saisir reste
  proposé, grisé, sans encombrer le rapport. Le choix vaut pour tout le rapport (bilan, les trois
  PDF, exports) et reste sur l'appareil.
- **Ce que les autres ont noté, dans la fiche** : en ouvrant une prise (ou un plan), on voit ce que
  les autres ont saisi sur la même prise — même plan, même numéro. Chaque ligne porte une barre :
  à la couleur de l'autre quand lui seul l'a remplie, verte quand on a noté la même chose, rouge
  quand on diffère ; sa valeur est dessous, un appui la reprend (une note s'ajoute à la sienne).
  Sur les bulles (résultat, étoile, notes rapides, météo, focale…), un rond à son initiale ;
  toucher la même bulle la confirme, elle s'entoure de vert. L'heure, les timecodes et la durée
  ne comptent pas. La fiche relit les saisies des autres toutes les quinze secondes, seulement
  celles qui ont changé.
- **Qui tourne quoi** : quand quelqu'un vise un plan pour le Moteur (l'anneau rouge de la carte),
  son rond à initiale apparaît sur l'anneau de ce plan chez tous les autres. Chaque personne a
  sa couleur, la même sur tous les appareils : sa place dans la liste de l'équipe.
- **La fiche d'un plan** : les éléments captés sont à chacun. On coche les siens sans toucher à
  ceux des autres ; ceux de Romain portent son rond, contour à sa couleur, et une case cochée à
  deux s'entoure de vert, comme dans la fiche d'une prise. La description VFX, la note et
  « Autre » sont aussi à chacun : on écrit la sienne (son rond à côté), celles des autres se lisent
  dessous, en italique, avec leur rond et leur prénom ; un texte d'avant, sans auteur connu (celui
  du découpage, ou tapé quand le champ était commun), s'y lit sous « Commun ». La liste, les filtres, les PDF et les exports
  prennent les éléments et les textes de tous. Une pastille dit qui a changé l'état. L'anneau du
  Moteur est à côté de la description.
- **La Préparation** (le découpage) : seul Simon la modifie (`PREPARATEURS`, en tête du script) ;
  les autres la consultent en lecture, jour par jour.
- **Le découpage est à tous, les prises à chacun** : la liste des plans se prépare dans Préparation
  (par une personne, jour par jour) et le serveur la reporte chez tout le monde ; chacun garde sa
  copie de ce qu'il note dessus (états, éléments captés). Quand deux personnes ont noté des choses
  différentes sur le même plan ou la même prise, Rapport → « Rapprocher les saisies » les met côte
  à côte.

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

**Retirer un prénom.** On l'enlève d'`EQUIPE`, en tête du script de la page, puis on retire son
espace : un appel `ops.php` avec `{ op: 'remplacer', db: { plans: [], prises: [], retire: true } }`
pour cet espace. Il sort de la liste du DIT, et le serveur ne lui recopie plus le découpage. Si
un appareil reprend un jour ce prénom, il repart sur le découpage de l'équipe, comme un nouveau
venu. Tom a été retiré ainsi le 29/09/2026, et les espaces d'essai aussi.

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
deux personnes ont rempli la même prise (même plan, même numéro), elle ne fait qu'une ligne, aux
deux noms : celles d'ici font foi, les autres comblent les vides, les notes s'ajoutent. Ce qui
compte et diffère — statut, à monter, focale, clip, carte, réglages… — est noté comme **écart** sur
la prise, et le journal DIT (PDF) le liste, une ligne par écart, avec un compte en tête de
journée. Le journal tient en deux parties, une journée par page : les prises retenues pour le
montage, sous l'en-tête qui compte la journée (le DIT réglé dans la fiche Journée ; les wranglers,
ceux qui ont saisi), puis les écarts entre les saisies, s'il y en a. L'heure, les timecodes et la durée ne comptent pas : un chrono oublié ou quelques secondes
d'écart ne sont pas un désaccord. Pour voir ces écarts en détail, ou pour en faire son projet :
« Rapprocher les saisies », juste en dessous dans le Rapport.

Sans serveur, chacun saisit de son côté, dans son navigateur, et personne ne voit les autres. Pour
tout réunir : chacun exporte sa sauvegarde (⚙ → Données → Sauvegarde JSON) et l'envoie au DIT, qui
la dépose dans Rapport → « Rapprocher les saisies ». Le rapport met les prises côte à côte, plan par
plan : un **écart** quand deux personnes ont écrit des valeurs différentes (statut, clip, carte,
timecodes, notes, réglages…), un **complément** quand une seule a rempli un champ, une **prise chez
un seul** quand une seule l'a saisie. « Garder la fusion comme projet » garde tout : les saisies de
ce navigateur font foi sur les écarts, les autres comblent les vides et apportent leurs prises en
plus. Chaque fichier est nommé d'après qui a saisi ses prises.

**La fiche data wrangling** (Rapport → **Data wrangling (PDF)**, à côté du DIT et du VFX) est faite pour trancher avant d'exporter le journal DIT et la fiche VFX. Elle va
chercher les saisies de chacun, puis donne une journée par page : les **écarts à trancher**, un par
ligne, avec une colonne par personne et une case à cocher quand la saisie fautive est corrigée dans
l'app ; puis les **prises notées par une seule personne** (un oubli chez les autres, ou une prise en
trop). Comme pour la fusion, seuls comptent les désaccords réels : ni l'heure, ni les timecodes, ni la
durée, ni les notes (elles s'ajoutent), ni ce qu'une seule personne a rempli.

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
espace (un plan s'y reconnaît à son identifiant, le même partout, sinon à sa séquence et son
numéro). Un plan sur lequel quelqu'un a déjà
des prises ne lui est jamais retiré. La production et les optiques suivent la même règle. Un
nouveau venu reçoit le découpage de l'équipe, mêmes plans et mêmes identifiants, et garde ses
prises. « Recharger le découpage » (⚙ → Données) remet les plans dans l'ordre du DT, garde ce
qui a été saisi dessus, replie les doublons et laisse les plans ajoutés sur le plateau à la
suite ; comme c'est une opération sur le découpage, elle vaut pour tout le monde. Depuis la
fiche d'un plan ouverte en Tournage, on ne supprime pas de plan : c'est dans Préparation.

**Préparer en nombre, détailler ensuite.** Préparation se parcourt jour par jour, avec la même
barre qu'en Tournage (« Tout » les montre à la suite). Dans l'en-tête de chaque jour, « Plans »
donne son nombre de plans : le monter pose autant de cartes vides à la fin du jour, à remplir
après ; le baisser ne retire que des cartes encore vides (sans numéro, sans description, sans
prise), les autres restent et la page le dit. « + Jour » ouvre le jour suivant (et y revient tant
qu'il est vide), « Supprimer le jour » retire le jour et ses plans après confirmation. Sur la
carte : ordre, séquence, shot, jour, décor, titre de séquence ; la distribution, à droite sous
les étiquettes, se coche dans un menu déroulant. Le titre et le décor d'une séquence valent pour
toute la séquence : tapés sur un plan, ils se posent sur les autres plans du même numéro, et un
plan qui change de séquence prend ceux qu'elle porte déjà. Les décors du tournage se déclarent
une fois (bouton « Décors » en Préparation, ou « + Ajouter un décor… » au bas du menu Décor) :
ils sont rangés dans la production, donc chez tout le monde, et proposés au champ Décor de chaque
plan. Dans la feuille Décors, « Modifier » renomme un décor partout où des plans le portent,
« Retirer » l'enlève de la liste et laisse ces plans sans décor, après confirmation.

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
  La pastille du jour affiché reste toujours en vue.
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
- **La focale qui n'est pas celle du plan** : le plan prévoit 14 mm, la prise dit 35 mm — la
  ligne de la prise la montre en orange avec ⚠, et la fiche le dit en tête. « 14 » vaut « 14 mm » ;
  un zoom prévu (« 18-35 ») accepte tout ce qui tombe dedans ; départ et arrivée comptent.
- **Saisie différée** (à côté de « Supprimer la prise ») : on la remplira plus tard. La prise
  reste dans « À compléter », marquée « saisie différée », tant qu'on ne retire pas la marque.
- **Prise non saisie**, quand on n'a pas eu le temps de la noter (les deux marques s'excluent) :
  la prise reste, marquée « non saisie » dans la liste. Elle sort de « À compléter », et quand l'équipe est réunie ce sont
  les saisies des autres qui comptent pour elle : ce que la page a repris de la prise d'avant ne
  fait pas de faux écart. Un second appui retire la marque.
- Dans la fiche : résultat (OK, NG, Série, Faux départ, Pick-up), note libre et mots rapides
  (Raccord, Jeu, Cadre…), nom de clip avec suggestion du suivant (bouton ＋1), relevés caméra
  pour le matchmove, réglages image, son.
- Caméra, carte, optique, réglages : repris automatiquement de la prise précédente. La focale est
  reprise telle quelle : le départ seul, ou le départ et l'arrivée après un zoom.
- **La carte, à côté du clip**, se lit dans son nom ARRI : `A_0001C0004` donne `A_0001` (le nom
  complet du fichier aussi). Elle suit le clip, « +1 » compris ; un identifiant tapé à la main
  qui n'a pas la forme d'une bobine (`1F6K`) n'est pas touché.
- **Cadrage et mouvement se choisissent à plusieurs** : on coche les tuiles, puis « Terminé » ;
  ils se gardent ensemble, « Poitrine / Américain », comme dans le découpage.
- **Seul le plan que le Moteur vise déplie ses prises** ; les autres les replient en une ligne
  (« 8 prises · 2 OK »), qu'un appui déplie. Viser un autre plan (son anneau, sa ligne, son
  « + Prise ») replie le précédent ; le plan touché reste à sa place à l'écran. Les filtres « À
  monter » et « Saisie par » montrent les prises partout.
- **Fusionner deux shots** tournés en un seul : fiche du plan gardé → « Fusionner avec un autre
  shot… », puis le shot à absorber. Ses prises passent sur le shot gardé, à la suite du plus
  grand numéro connu chez tous (la prise 1 du 06 devient partout la même prise du 05, et garde
  en note d'où elle vient) : chaque appareil déplace les siennes dès qu'il reçoit la fusion. Ses
  descriptions, notes et éléments captés, ceux de chacun, rejoignent le shot gardé ; il passe en
  « Abandonné », marqué « fusionné dans 05 », et le shot gardé porte « + 06 ». Ce n'est pas
  facile à défaire : la page demande confirmation.
- **Le bouton Retour du navigateur** (le geste retour du téléphone) revient en arrière dans le
  site au lieu de le quitter : il ferme la fiche ouverte, ramène d'une prise à son plan, et d'une
  page à l'autre (Préparation, Tournage, Rapport).
- **« Tourné »** s'affiche sur un shot une fois qu'on est passé à la suite : dès la première prise
  notée sur un autre shot. Le shot qu'on tourne encore ne le dit pas.
- **« + Plan »** demande d'abord le numéro du shot (modifiable ensuite dans sa fiche) ; le plan
  est au découpage, il arrive chez toute l'équipe.
- Pendant une prise, le bouton « Coupez » respire lentement.
- Supprimer une prise, un plan ou une carte : « Annuler » dans le bandeau pendant 7 secondes.

## Divers

- ☼ / ☾ en haut : thème clair pour le plein soleil, sombre pour la nuit.
- La pastille en haut porte le prénom de qui saisit sur cet appareil ; son point dit l'état du
  réseau et le nombre de personnes connectées (une personne sur deux onglets, ou un navigateur
  relancé, ne compte qu'une fois ; un onglet fermé sort aussitôt de la liste), et elle ajoute
  « hors ligne » ou « local » quand il n'y a pas de serveur au bout.
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

Onglet **Rapport** → **VFX (PDF)**. La fiche est écrite par la page, dans la charte du journal
DIT, et se télécharge directement. Elle reprend le jour choisi dans la rangée du haut (`Tout` = une
journée par page) : en tête, le compte de la journée (plans tournés, plans VFX, prises retenues,
plans avec éléments, cartes) ; puis chaque plan tourné, avec ce qu'il faut au compositing :

- ce que le DT demande (description VFX, assets, tags VFX / CG), dans un encadré ;
- les réglages de la prise qui fait foi : ce que tous les plans du jour partagent (caméra, format,
  cadence, exposition, couleur, objectif, diaph, filtres) s'écrit une fois en tête de journée ; chaque
  plan garde le sien — **optique** (focale, point…), **matchmove** (hauteur et d'où elle est mesurée,
  pan / tilt / roll, mouvement, support, météo en extérieur) et **éléments captés** (HDRI, charte,
  boule chrome, cleanplate, lidar…) ;
- toutes les prises du plan, comme dans le journal : la retenue en gras sur fond crème, le statut en
  couleur, la carte, la durée, la note (une plaque ou un plan B s'y cache souvent) et qui l'a saisie.

Les écarts de saisie n'y figurent pas : ils se tranchent avant, sur la fiche data wrangling.

Les plans sans prise ni élément ne sont pas imprimés : la fiche ne contient que ce qui a été tourné.
Sur « Toute l'équipe », elle porte sur les saisies réunies, comme le journal.
- Port différent : `py serveur.py 9000`.

## Vérifier que rien n'est cassé

Vingt-cinq scripts pilotent un Chrome invisible sur un serveur et un dossier de données temporaires :
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
py tests/verif_journal_dit.py      le journal DIT en PDF : par jour, prises retenues pour le montage, puis écarts entre saisies
py tests/verif_fiche_vfx.py        la fiche VFX en PDF : par jour, chaque plan tourné avec ce qu'il faut au compositing
py tests/verif_prep_cadrage.py     en préparation, plusieurs cadrages sur un plan
py tests/verif_plans_par_jour.py   préparer jour par jour : nombre de plans, jour de plus ou de moins, distribution cochée
py tests/verif_viser.py            l'anneau des cartes choisit le plan que le Moteur va tourner
py tests/verif_mail.py             le journal DIT par mail, à la main et à l'heure dite
py tests/verif_rapprochement.py    rapprocher les saisies de plusieurs personnes, la fiche data wrangling, et la fusion
py tests/verif_personnes.py         chacun ses saisies sur le site, et à qui revient le carnet d'avant
py tests/verif_interroger.py       la page en mode php, comme chez l'hébergeur : elle interroge au lieu d'écouter
py tests/verif_coupure.py          saisir en zone blanche, fermer l'appli avant le retour du réseau : rien ne se perd
py tests/verif_choix_equipe.py     le DIT réunit une personne, plusieurs ou toutes ; « Tous », ce sont ceux qui ont saisi
py tests/verif_a_deux.py           dans la fiche, ce que les autres ont noté sur la même prise, à reprendre ou confirmer
py tests/verif_pas_saisie.py       « prise non saisie », et la focale de la prise qui n'est pas celle du plan
py tests/verif_saisie_plateau.py   focale reprise, carte lue dans le clip, cadrage multiple, prises repliées, bouton Retour
py tests/verif_fusion.py           fusionner deux shots : les prises de chacun suivent, avec les mêmes numéros
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
