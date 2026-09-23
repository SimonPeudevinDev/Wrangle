# Wrangle — journal de plateau

Un carnet de DIT / data wrangler : jours, séquences, plans, prises, cartes et rapport de fin de journée.
La page est `wrangle.html`, avec sa feuille de style et son logo dans `public/` : garder les deux ensemble. Le serveur `serveur.py` permet de saisir à plusieurs en même temps.

## Lancer sur le plateau (plusieurs appareils)

1. Sur un ordinateur du plateau (celui du DIT), double-cliquer sur **`Lancer.bat`**.
   Une fenêtre noire s'ouvre et affiche les adresses ; la page s'ouvre dans le navigateur.
2. Sur chaque téléphone ou tablette, se connecter au **même Wi-Fi** et ouvrir dans le navigateur
   l'adresse affichée dans la fenêtre noire, par exemple `http://192.168.1.20:8765`.
   Cette adresse est aussi rappelée dans la page, bouton ⚙ en haut à droite, section « Équipe connectée ».
3. Chaque appareil donne un prénom à la première ouverture. Il apparaît sur les prises ajoutées
   et les autres voient sur quel plan chacun travaille (initiale à côté de la prise).

Chaque modification part au serveur champ par champ et arrive chez tous en moins d'une seconde.
Deux personnes peuvent remplir la même prise : seul le champ modifié est envoyé.
Si deux appareils ajoutent une prise au même plan au même moment, le serveur attribue les numéros.

Laisser la fenêtre noire ouverte pendant le tournage. `Ctrl+C` ou fermer la fenêtre arrête le serveur
(le projet est enregistré avant l'arrêt).

Sur iPhone / iPad : Safari > Partager > « Sur l'écran d'accueil » donne une icône plein écran.

## Où sont les données

- `data/projet.json` : le projet partagé, réécrit à chaque modification.
- `data/sauvegardes/` : une copie horodatée au démarrage puis toutes les 10 minutes dès qu'il y a
  du nouveau (60 dernières conservées). Pour revenir en arrière : arrêter le serveur, copier la
  sauvegarde voulue sur `data/projet.json`, relancer.
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

Première mise en route : si le serveur n'a encore aucun projet, le premier appareil connecté envoie
le sien (découpage compris, et les prises déjà saisies dans ce navigateur s'il y en a).

## Travailler seul, sans serveur

Ouvrir directement `wrangle.html` dans un navigateur : la page travaille seule, données dans le
navigateur, comme avant. La pastille en haut indique « Local ».

## Saisir à plusieurs hors du plateau

Le serveur n'a pas besoin d'être sur le Wi-Fi du plateau. Posé sur une machine joignable depuis
internet, il laisse chacun saisir depuis son téléphone en 4G, sous son prénom, tout le monde
voyant les saisies des autres en direct — exactement comme sur le plateau. Deux précautions.

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

Sans serveur, chacun saisit de son côté, dans son navigateur, et personne ne voit les autres. Pour
tout réunir : chacun exporte sa sauvegarde (⚙ → Données → Sauvegarde JSON) et l'envoie au DIT, qui
la dépose dans Rapport → « Rapprocher les saisies ». Le rapport met les prises côte à côte, plan par
plan : un **écart** quand deux personnes ont écrit des valeurs différentes (statut, clip, carte,
timecodes, notes, réglages…), un **complément** quand une seule a rempli un champ, une **prise chez
un seul** quand une seule l'a saisie. « Garder la fusion comme projet » garde tout : les saisies de
ce navigateur font foi sur les écarts, les autres comblent les vides et apportent leurs prises en
plus. « Écarts (PDF) » sort le même rapport en PDF. Chaque fichier est nommé d'après qui a saisi ses
prises.

**Sans échange de fichiers.** Quand le site est servi par un hébergeur qui exécute PHP (OVH), la
boîte de dépôt `depot/` fait le tour : chacun clique ⚙ → Données → « Déposer mes saisies », et ses
saisies partent chez l'hébergeur sous son prénom (un fichier par personne, le dernier dépôt
remplace le précédent, hors de portée du web). Le DIT clique « Récupérer les dépôts » dans le
rapprochement. Pas de clé ni de mot de passe : le site est privé, seule l'équipe en connaît
l'adresse, et le prénom choisi à l'entrée suffit.

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
  (Raccord, Jeu, Cadre…), nom de clip avec suggestion du suivant (bouton ＋1), photo de référence
  (moniteur, clap), relevés caméra pour le matchmove, réglages image, son.
- Caméra, carte, optique, réglages : repris automatiquement de la prise précédente.
- Supprimer une prise, un plan ou une carte : « Annuler » dans le bandeau pendant 7 secondes.

## Divers

- ☼ / ☾ en haut : thème clair pour le plein soleil, sombre pour la nuit.
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
2. **Pour les VFX**, plan par plan : la vignette du découpage, ce que le DT demandait, la prise qui
   fait foi avec son optique et ses réglages image, les **éléments captés** (HDRI, charte, boule
   chrome, fond vert…) et les **relevés matchmove** (point de map, hauteur, mesuré depuis, pan /
   tilt / roll). Les autres prises sont rappelées en une ligne, pour retrouver un plan B.
3. **Médias** : sur quelle carte sont les rushes, combien de copies, checksum vérifié ou non.

Les plans sans prise ni élément ne sont pas imprimés : la fiche ne contient que ce qui a été tourné.
Dans la fenêtre d'impression, choisir « Enregistrer au format PDF ».
- Port différent : `py serveur.py 9000`.

## Vérifier que rien n'est cassé

Quatorze scripts pilotent un Chrome invisible sur un serveur et un dossier de données temporaires :
le projet réel n'est jamais touché.

```
py tests/lancer_scenario.py        deux appareils qui saisissent en même temps
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

`py outils/construire_site.py` fabrique ce site dans `site/` : il reprend `wrangle.html` tel quel
sous le nom `index.html`, découpage et vignettes de la production compris (`window.DT_SEED`,
`window.DT_THUMBS` et le dossier `public/vignettes/`). Tout le monde ouvre donc le site sur les plans du tournage, comme sur le
plateau. Chacun garde ensuite ses prises dans son navigateur ; ⚙ > Données > « Recharger le
découpage » remet les plans à jour sans toucher aux prises.

Pour publier un carnet vide à la place (sans le découpage ni ses vignettes) : `py outils/construire_site.py --vide`.
La page pèse alors 200 Ko au lieu de 1,4 Mo, et un garde-fou refuse de construire s'il restait une
trace des données. Le fichier du plateau n'est jamais touché.

Pour voir le résultat avant de publier : ouvrir `site/index.html` directement dans le navigateur.
(Par `http://localhost`, la page se croit sur un serveur de plateau et affiche « Hors ligne » :
c'est normal, `localhost` est une adresse locale.)

Publier : `git push`. GitHub relance la construction et met le site en ligne en une minute
(`.github/workflows/publier.yml`). Le nom de domaine est dans le fichier `CNAME` à la racine.

Le même automatisme peut aussi déposer le site chez OVH, par FTP, dans le `www` de l'hébergement :
il suffit de poser trois secrets dans GitHub (Settings > Secrets and variables > Actions) :
`OVH_FTP_HOTE` (`ftp.clusterNNN.hosting.ovh.net`), `OVH_FTP_UTILISATEUR` et `OVH_FTP_MOTDEPASSE`.
Sans eux, l'étape est sautée. Pour que le nom de domaine mène chez OVH plutôt que chez GitHub :
dans l'espace client OVH, l'hébergement > Multisite > ajouter le domaine avec sa zone DNS, puis
commander le certificat SSL gratuit ; côté GitHub, retirer le domaine personnalisé des réglages
Pages et supprimer le fichier `CNAME`.

Le mode partagé s'allume quand `serveur.py` sert la page : il la signe en tête
(`window.WRANGLE_SERVEUR`), où qu'il soit posé — Wi-Fi du plateau, nom de domaine, réseau privé.
Sans cette signature, la page juge sur l'adresse (`serveurPossible`) : `localhost`, IP privée, nom
en `.local` ou sans point. Le site publié n'a pas de serveur derrière et n'est pas signé : il reste
en mode local, chacun ses données dans son navigateur.
