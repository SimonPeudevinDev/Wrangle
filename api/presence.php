<?php
// Qui est la, et ce qu'il regarde : POST { client, nom, actif, espace } -> { ok } ;
// { client, quitte: true } : l'onglet est ferme.
require __DIR__ . '/commun.php';
$c = corps();
choisir_espace(espace_demande($c));
$client = couper($c->client ?? '', 40);
if ($client === '') {
    repondre(400, ['erreur' => 'client attendu']);
}
// un onglet qu'on ferme le dit ({ quitte: true }) : il sort de la liste tout de suite
if (!empty($c->quitte)) {
    oublier_presence($client);
    repondre(200, ['ok' => true]);
}
noter_presence($client, isset($c->nom) ? (string) $c->nom : null, isset($c->actif) ? (string) $c->actif : null);
repondre(200, ['ok' => true]);
