<?php
// Les comptes de l'equipe, pour le DIT : POST { jeton } -> { comptes: [{ nom, dit }] }.
require __DIR__ . '/commun.php';
$q = qui();
if (!$q['dit']) {
    repondre(403, ['erreur' => 'réservé au DIT']);
}
$liste = [];
foreach (lire_comptes() as $x) {
    $liste[] = ['nom' => $x['nom'], 'dit' => !empty($x['dit'])];
}
usort($liste, function ($a, $b) { return strcmp($a['nom'], $b['nom']); });
repondre(200, ['comptes' => $liste]);
