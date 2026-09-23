<?php
// L'etat d'un espace : son projet, sa revision, et qui est la (tous espaces).
require __DIR__ . '/commun.php';
choisir_espace(espace_demande());
verrouiller(false);
$db = lire_projet();
$rev = lire_rev();
deverrouiller();
repondre(200, ['db' => $db, 'rev' => $rev, 'espace' => $ESPACE, 'presence' => liste_presence(),
               'adresses' => [], 'serveur' => 'php']);
