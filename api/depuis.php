<?php
// Ce qui a change dans un espace depuis une revision : GET ?rev=N&client=…&nom=…&espace=…
// Rend { rev, ops: [{ client, rev, ops }…], presence } quand le journal suffit,
// { rev, db, presence } quand il faut le projet entier (premiere fois, trop de
// retard, remplacement entre-temps). db vaut null tant que l'espace est vide :
// l'appareil envoie alors le sien. Tient lieu de flux : la page passe ici
// toutes les deux secondes.
require __DIR__ . '/commun.php';
choisir_espace(espace_demande());
$rev = (int) ($_GET['rev'] ?? 0);
$client = couper($_GET['client'] ?? '', 40);
$nom = isset($_GET['nom']) ? (string) $_GET['nom'] : null;

verrouiller(false);
$actuel = lire_rev();
$rep = ['rev' => $actuel];
if ($rev <= 0 || $rev > $actuel) {
    $rep['db'] = lire_projet();
} elseif ($rev < $actuel) {
    $entrees = journal_depuis($rev);
    if ($entrees === null) {
        $rep['db'] = lire_projet();
    } else {
        $rep['ops'] = $entrees;
    }
}
deverrouiller();

if ($nom !== null) {
    noter_nom($nom);
}
noter_presence($client, $nom);
$rep['presence'] = liste_presence();
repondre(200, $rep);
