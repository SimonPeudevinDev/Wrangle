<?php
// Les operations d'un appareil : POST { client, nom, espace, ops } -> { rev, ops }.
// Appliquees au projet de l'espace sous verrou, notees au journal pour ses
// autres appareils, renvoyees a l'emetteur telles que faites (numeros corriges).
require __DIR__ . '/commun.php';
$c = corps();
if ($c === null) {
    repondre(400, ['erreur' => 'JSON attendu']);
}
choisir_espace(espace_demande($c));
$client = couper($c->client ?? '', 40);
$ops = $c->ops ?? null;
if ($client === '' || !is_array($ops)) {
    repondre(400, ['erreur' => 'client et ops attendus']);
}

verrouiller();
$db = lire_projet();
$rev = lire_rev();
$avant = cles_avant($db);
// un nouveau venu (siVide, espace vide) recoit le decoupage de l'equipe et garde ses prises
$siVide = false;
foreach ($ops as $i => $op) {
    if (is_object($op) && ($op->op ?? '') === 'remplacer' && !empty($op->siVide)) {
        $siVide = true;
        if ($db === null && is_object($op->db ?? null) && is_array($op->db->plans ?? null)) {
            $donneur = donneur_decoupage($ESPACE);
            if ($donneur) {
                $ops[$i] = (object) ['op' => 'remplacer', 'siVide' => true,
                                     'db' => traduire((object) ['op' => 'remplacer', 'db' => $donneur], [], normaliser($op->db))->db];
            }
        }
    }
}
$faites = appliquer($db, $ops);
if ($faites) {
    $rev++;
    ecrire_projet($db);
    ecrire_rev($rev);
    journal_ajouter($rev, $client, $faites);
    sauvegarder_si_besoin($db);
}
if (isset($c->nom)) {
    noter_nom($c->nom);
}
deverrouiller();

// le decoupage est a tout le monde : ce qui n'est pas une prise part chez les
// autres ; l'arrivee d'un nouveau (siVide) ou un espace qu'on vide, non
if ($faites && $ESPACE !== 'commun') {
    $communs = [];
    foreach ($faites as $op) {
        if (($op->op ?? '') === 'remplacer' && ($siVide || empty($op->db->plans))) {
            continue;
        }
        $communs[] = $op;
    }
    if ($communs) {
        propager($ESPACE, $communs, $avant, $client);
    }
}
noter_presence($client, isset($c->nom) ? (string) $c->nom : null);
repondre(200, ['rev' => $rev, 'ops' => $faites]);
