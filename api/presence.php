<?php
// Qui est la, et ce qu'il regarde : POST { client, nom, actif, espace } -> { ok }.
require __DIR__ . '/commun.php';
$c = corps();
choisir_espace(espace_demande($c));
$client = couper($c->client ?? '', 40);
if ($client === '') {
    repondre(400, ['erreur' => 'client attendu']);
}
noter_presence($client, isset($c->nom) ? (string) $c->nom : null, isset($c->actif) ? (string) $c->actif : null);
repondre(200, ['ok' => true]);
