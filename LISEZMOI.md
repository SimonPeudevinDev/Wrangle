# Wrangle — journal de plateau

Un carnet de DIT / data wrangler : jours, séquences, plans, prises, cartes et rapport de fin de journée.
La page est `dit-log.html`, avec sa feuille de style et son logo dans `public/` : garder les deux ensemble. Le serveur `serveur.py` permet de saisir à plusieurs en même temps.

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

Première mise en route : si le serveur n'a encore aucun projet, le premier appareil connecté envoie
le sien (découpage compris, et les prises déjà saisies dans ce navigateur s'il y en a).

## Travailler seul, sans serveur

Ouvrir directement `dit-log.html` dans un navigateur : la page travaille seule, données dans le
navigateur, comme avant. La pastille en haut indique « Local ».

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
- Le logo : `ref/logo-wrangle.svg` (signe + mot) et `ref/logo-wrangle-mark.svg` (signe seul).
  Le signe est aussi dans la page, en haut à gauche et en icône d'onglet. Il prend la couleur
  du thème : ses coutures sont des découpes, pas du blanc, donc il tient sur n'importe quel fond.
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

## Publier le site

La page marche aussi toute seule sur Internet : données dans le navigateur de chacun, sans serveur
ni synchro. C'est ce qui est publié sur le nom de domaine.

`py outils/construire_site.py` fabrique ce site dans `site/` : il reprend `dit-log.html` tel quel
sous le nom `index.html`, découpage et vignettes de la production compris (`window.DT_SEED`,
`window.DT_THUMBS`). Tout le monde ouvre donc le site sur les plans du tournage, comme sur le
plateau. Chacun garde ensuite ses prises dans son navigateur ; ⚙ > Données > « Recharger le
découpage » remet les plans à jour sans toucher aux prises.

Pour publier un carnet vide à la place (sans le découpage) : `py outils/construire_site.py --vide`.
La page pèse alors 200 Ko au lieu de 1,4 Mo, et un garde-fou refuse de construire s'il restait une
trace des données. Le fichier du plateau n'est jamais touché.

Pour voir le résultat avant de publier : ouvrir `site/index.html` directement dans le navigateur.
(Par `http://localhost`, la page se croit sur un serveur de plateau et affiche « Hors ligne » :
c'est normal, `localhost` est une adresse locale.)

Publier : `git push`. GitHub relance la construction et met le site en ligne en une minute
(`.github/workflows/publier.yml`). Le nom de domaine est dans le fichier `CNAME` à la racine.

Le mode partagé ne s'allume que sur une adresse de plateau — `localhost`, une IP privée, un nom en
`.local` ou un nom sans point (`serveurPossible` dans la page). Sur un vrai nom de domaine, la page
reste en mode local : il n'y a pas de `serveur.py` derrière.
