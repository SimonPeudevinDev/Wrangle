<?php
// Qui est la, et ce qu'il regarde : POST { client, nom, actif } -> { ok }.
require __DIR__ . '/commun.php';
$c = corps();
$client = couper($c->client ?? '', 40);
if ($client === '') {
    repondre(400, ['erreur' => 'client attendu']);
}
noter_presence($client, isset($c->nom) ? (string) $c->nom : null, isset($c->actif) ? (string) $c->actif : null);
repondre(200, ['ok' => true]);
