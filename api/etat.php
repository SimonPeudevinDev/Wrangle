<?php
// L'etat du serveur : le projet partage, sa revision, qui est la.
require __DIR__ . '/commun.php';
verrouiller(false);
$db = lire_projet();
$rev = lire_rev();
deverrouiller();
repondre(200, ['db' => $db, 'rev' => $rev, 'presence' => liste_presence(), 'adresses' => [], 'serveur' => 'php']);
