<?php
// Les operations d'un appareil : POST { client, nom, ops } -> { rev, ops }.
// Appliquees au projet sous verrou, notees au journal pour les autres,
// renvoyees a l'emetteur telles que faites (numeros de prise corriges).
require __DIR__ . '/commun.php';
$c = corps();
if ($c === null) {
    repondre(400, ['erreur' => 'JSON attendu']);
}
$client = couper($c->client ?? '', 40);
$ops = $c->ops ?? null;
if ($client === '' || !is_array($ops)) {
    repondre(400, ['erreur' => 'client et ops attendus']);
}

verrouiller();
$db = lire_projet();
$rev = lire_rev();
$faites = appliquer($db, $ops);
if ($faites) {
    $rev++;
    ecrire_projet($db);
    ecrire_rev($rev);
    journal_ajouter($rev, $client, $faites);
    sauvegarder_si_besoin($db);
}
deverrouiller();

noter_presence($client, isset($c->nom) ? (string) $c->nom : null);
repondre(200, ['rev' => $rev, 'ops' => $faites]);
