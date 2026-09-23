<?php
// Wrangle, le serveur de plateau chez l'hebergeur : ce que les scripts d'api/
// partagent. Memes appels et memes reponses que serveur.py, a une difference
// pres : pas de flux, la page interroge depuis.php toutes les deux secondes.
// Le projet, le journal des operations, la presence et les sauvegardes vivent
// dans donnees/, interdit au web.
//
// Chacun a son espace, nomme d'apres son prenom (« marie-lou ») : son projet,
// son journal, ses sauvegardes, sur tous ses appareils. Il ne voit que ses
// saisies ; le DIT reunit celles de tous dans le rapprochement, par
// espaces.php puis etat.php?espace=… Chaque appel dit son espace (?espace=
// ou { espace } dans le corps) ; sans, c'est l'espace « commun ».
//
//   etat.php      GET   ?espace=…                      { db, rev, presence, adresses }
//   depuis.php    GET   ?rev=N&client=…&nom=…&espace=…  -> ce qui a change depuis N
//   ops.php       POST  { client, nom, espace, ops }   -> { rev, ops }
//   presence.php  POST  { client, nom, actif, espace } -> { ok }
//   espaces.php   GET   les espaces qui ont un projet : { espaces: [{ espace, nom, rev, plans, prises, quand }] }
//   mail.php      GET / POST : le journal DIT par mail

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

define('DONNEES', __DIR__ . '/donnees');
define('JOURNAL_GARDE', 400);        // operations gardees pour les appareils en retard
define('SAUV_TOUTES_LES', 10 * 60);  // secondes entre deux sauvegardes horodatees
define('SAUV_CONSERVEES', 60);
define('PRESENCE_EXPIRE', 90);       // secondes sans nouvelle d'un appareil avant retrait
define('JSON_SORTIE', JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

function repondre($code, $obj) {
    http_response_code($code);
    echo json_encode($obj, JSON_SORTIE);
    exit;
}

// le corps JSON de la requete, en objets (un {} vide reste un {})
function corps() {
    $c = json_decode(file_get_contents('php://input'));
    return is_object($c) ? $c : null;
}

function couper($s, $n) {
    return mb_substr((string) $s, 0, $n);
}

// ------------------------------------------------------------- Espaces ---

$ESPACE = 'commun';

// l'espace demande par l'appel : ?espace=… ou { espace } dans le corps, en lettres
// minuscules, chiffres et tirets ; a defaut, « commun »
function espace_demande($corps = null) {
    $e = $_GET['espace'] ?? (is_object($corps) ? ($corps->espace ?? '') : '');
    $e = trim(strtolower(preg_replace('/[^A-Za-z0-9-]+/', '-', (string) $e)), '-');
    return $e === '' ? 'commun' : substr($e, 0, 40);
}

function choisir_espace($e) {
    global $ESPACE;
    $ESPACE = $e;
}

function dossier_espace() {
    global $ESPACE;
    return DONNEES . '/espaces/' . $ESPACE;
}

// le prenom tel que la personne l'ecrit, pour la liste des espaces
function noter_nom($nom) {
    $nom = couper(trim((string) $nom), 40);
    $f = dossier_espace() . '/nom.txt';
    if ($nom !== '' && (!file_exists($f) || file_get_contents($f) !== $nom)) {
        file_put_contents($f, $nom);
    }
}

// ------------------------------------------------------------ Fichiers ---

function preparer() {
    foreach ([DONNEES, dossier_espace(), dossier_espace() . '/journal', dossier_espace() . '/sauvegardes'] as $d) {
        if (!is_dir($d)) {
            mkdir($d, 0755, true);
        }
    }
    if (!file_exists(DONNEES . '/.htaccess')) {
        file_put_contents(DONNEES . '/.htaccess', "Require all denied\n");
    }
}

$VERROU = null;

// un seul script a la fois modifie le projet d'un espace ; les lecteurs se partagent le verrou
function verrouiller($exclusif = true) {
    global $VERROU;
    preparer();
    $VERROU = fopen(dossier_espace() . '/verrou', 'c');
    if ($VERROU) {
        flock($VERROU, $exclusif ? LOCK_EX : LOCK_SH);
    }
}

function deverrouiller() {
    global $VERROU;
    if ($VERROU) {
        flock($VERROU, LOCK_UN);
        fclose($VERROU);
        $VERROU = null;
    }
}

function lire_json($chemin) {
    if (!file_exists($chemin)) {
        return null;
    }
    return json_decode(file_get_contents($chemin));
}

// ecriture atomique : fichier temporaire puis remplacement
function ecrire_json($chemin, $obj) {
    $tmp = $chemin . '.' . getmypid() . '.tmp';
    if (file_put_contents($tmp, json_encode($obj, JSON_SORTIE)) === false || !rename($tmp, $chemin)) {
        @unlink($tmp);
        repondre(500, ['erreur' => 'écriture impossible sur le serveur']);
    }
}

function lire_rev() {
    $f = dossier_espace() . '/rev.txt';
    return file_exists($f) ? (int) file_get_contents($f) : 0;
}

function ecrire_rev($rev) {
    file_put_contents(dossier_espace() . '/rev.txt', (string) $rev, LOCK_EX);
}

// -------------------------------------------------------------- Projet ---

function normaliser($db) {
    if (!is_object($db)) {
        $db = new stdClass;
    }
    if (!isset($db->version)) {
        $db->version = 2;
    }
    if (!isset($db->prod) || !is_object($db->prod)) {
        $db->prod = new stdClass;
    }
    if (!isset($db->optiques) || !is_array($db->optiques)) {
        $db->optiques = [];
    }
    foreach (['plans', 'prises'] as $c) {
        if (!isset($db->$c) || !is_array($db->$c)) {
            $db->$c = [];
        }
    }
    unset($db->ui);   // preference d'affichage : propre a chaque appareil
    foreach ($db->plans as $p) {
        if (is_object($p) && (!isset($p->elements) || !is_object($p->elements))) {
            $p->elements = new stdClass;
        }
    }
    return $db;
}

// le projet de l'espace, ou null tant qu'aucun appareil n'en a envoye un
function lire_projet() {
    $db = lire_json(dossier_espace() . '/projet.json');
    if (!is_object($db) || empty($db->plans)) {
        return null;
    }
    return normaliser($db);
}

function ecrire_projet($db) {
    ecrire_json(dossier_espace() . '/projet.json', $db);
}

// une copie horodatee toutes les dix minutes des qu'il y a du nouveau, 60 gardees
function sauvegarder_si_besoin($db) {
    $f = dossier_espace() . '/derniere_sauv.txt';
    $derniere = file_exists($f) ? (int) file_get_contents($f) : 0;
    if (time() - $derniere < SAUV_TOUTES_LES) {
        return;
    }
    ecrire_json(dossier_espace() . '/sauvegardes/projet_' . date('Y-m-d_His') . '.json', $db);
    file_put_contents($f, (string) time());
    $anciennes = glob(dossier_espace() . '/sauvegardes/projet_*.json') ?: [];
    sort($anciennes);
    foreach (array_slice($anciennes, 0, max(0, count($anciennes) - SAUV_CONSERVEES)) as $x) {
        @unlink($x);
    }
}

// ------------------------------------------------------------- Journal ---
// Une entree par revision : { rev, client, ops }. Un « remplacer » y est note
// sans son contenu : un appareil en retard dessus recoit le projet entier.

function journal_ajouter($rev, $client, $ops) {
    $entree = ['rev' => $rev, 'client' => $client, 'ops' => $ops];
    ecrire_json(dossier_espace() . '/journal/' . sprintf('%012d', $rev) . '.json', $entree);
    $fichiers = glob(dossier_espace() . '/journal/*.json') ?: [];
    sort($fichiers);
    foreach (array_slice($fichiers, 0, max(0, count($fichiers) - JOURNAL_GARDE)) as $x) {
        @unlink($x);
    }
}

// les entrees apres la revision $rev, ou null s'il faut le projet entier
// (trop en retard, ou un remplacement entre-temps)
function journal_depuis($rev) {
    $fichiers = glob(dossier_espace() . '/journal/*.json') ?: [];
    sort($fichiers);
    $entrees = [];
    $attendu = $rev + 1;
    foreach ($fichiers as $f) {
        $n = (int) basename($f, '.json');
        if ($n <= $rev) {
            continue;
        }
        if ($n !== $attendu) {
            return null;
        }
        $e = lire_json($f);
        if (!is_object($e)) {
            return null;
        }
        foreach ($e->ops as $op) {
            if (($op->op ?? '') === 'remplacer') {
                return null;
            }
        }
        $entrees[] = $e;
        $attendu++;
    }
    return $entrees;
}

// ------------------------------------------------------------ Presence ---
// Qui est la et ce qu'il regarde, tous espaces confondus : l'equipe se voit
// connectee, sans voir les saisies des autres. Chaque interrogation renouvelle
// la presence de l'appareil ; passe le delai, il disparait de la liste.

function noter_presence($client, $nom = null, $actif = null) {
    global $ESPACE;
    if ($client === '') {
        return;
    }
    preparer();
    $v = fopen(DONNEES . '/presence.verrou', 'c');
    if ($v) {
        flock($v, LOCK_EX);
    }
    $liste = lire_json(DONNEES . '/presence.json');
    if (!is_object($liste)) {
        $liste = new stdClass;
    }
    $p = $liste->$client ?? (object) ['nom' => '', 'actif' => '', 'espace' => '', 'vu' => 0];
    $change = $nom !== null && $p->nom !== couper($nom, 40)
           || $actif !== null && $p->actif !== couper($actif, 80)
           || ($p->espace ?? '') !== $ESPACE
           || time() - $p->vu >= 10;     // les battements ne reecrivent pas le fichier a chaque fois
    if ($change) {
        if ($nom !== null) {
            $p->nom = couper($nom, 40);
        }
        if ($actif !== null) {
            $p->actif = couper($actif, 80);
        }
        $p->espace = $ESPACE;
        $p->vu = time();
        $liste->$client = $p;
        foreach ($liste as $c => $x) {
            if (time() - ($x->vu ?? 0) > PRESENCE_EXPIRE) {
                unset($liste->$c);
            }
        }
        ecrire_json(DONNEES . '/presence.json', $liste);
    }
    if ($v) {
        flock($v, LOCK_UN);
        fclose($v);
    }
}

function liste_presence() {
    $liste = lire_json(DONNEES . '/presence.json');
    $sortie = [];
    if (is_object($liste)) {
        foreach ($liste as $c => $p) {
            if (time() - ($p->vu ?? 0) <= PRESENCE_EXPIRE) {
                $sortie[] = ['client' => $c, 'nom' => $p->nom ?? '', 'actif' => $p->actif ?? '', 'espace' => $p->espace ?? ''];
            }
        }
    }
    return $sortie;
}

// ---------------------------------------------------------- Operations ---
// La meme logique que serveur.py : les operations d'un appareil, appliquees
// au projet, parfois corrigees (numero de prise deja pris) ou completees
// (renumerotation apres suppression). Retourne ce qui a ete fait.

function collection($db, $kind) {
    $c = ['plan' => 'plans', 'prise' => 'prises'];
    return ($db !== null && isset($c[$kind])) ? $c[$kind] : null;
}

function trouver($db, $kind, $id) {
    $c = collection($db, $kind);
    if ($c === null || !$id) {
        return null;
    }
    foreach ($db->$c as $e) {
        if (is_object($e) && isset($e->id) && $e->id === $id) {
            return $e;
        }
    }
    return null;
}

// ou inserer un plan : juste apres celui-ci, en tete si '' , a la fin si introuvable
function place_apres($liste, $apres) {
    if ($apres === '' || $apres === null) {
        return 0;
    }
    foreach ($liste as $i => $p) {
        if (isset($p->id) && $p->id === $apres) {
            return $i + 1;
        }
    }
    return count($liste);
}

function fusionner($cible, $data) {
    foreach ($data as $k => $v) {
        $cible->$k = $v;
    }
}

function appliquer(&$db, $ops) {
    $sortie = [];
    foreach ($ops as $op) {
        if (!is_object($op)) {
            continue;
        }
        $t = $op->op ?? null;
        $kind = $op->kind ?? null;

        if ($t === 'remplacer') {
            $d = $op->db ?? null;
            if (!is_object($d) || !isset($d->plans)) {
                continue;
            }
            // envoi initial d'un appareil qui a trouve le serveur vide : si un autre
            // appareil l'a devance entre-temps, son projet reste, celui-ci est ignore
            if (!empty($op->siVide) && $db !== null) {
                continue;
            }
            $db = normaliser($d);
            $sortie[] = (object) ['op' => 'remplacer'];
            continue;
        }
        if ($db === null) {
            continue;   // rien a modifier tant qu'aucun projet n'est charge
        }

        if ($t === 'patch') {
            $data = $op->data ?? null;
            if (!is_object($data)) {
                continue;
            }
            if ($kind === 'prod') {
                fusionner($db->prod, $data);
                $sortie[] = (object) ['op' => 'patch', 'kind' => 'prod', 'data' => $data];
            } else {
                $e = trouver($db, $kind, $op->id ?? null);
                if ($e !== null) {
                    fusionner($e, $data);
                    $sortie[] = (object) ['op' => 'patch', 'kind' => $kind, 'id' => $op->id, 'data' => $data];
                }
            }
        } elseif ($t === 'add') {
            $data = $op->data ?? null;
            $c = collection($db, $kind);
            if ($c === null || !is_object($data) || empty($data->id)) {
                continue;
            }
            $existant = trouver($db, $kind, $data->id);
            if ($existant !== null) {   // deja recu (renvoi apres coupure) : simple mise a jour
                fusionner($existant, $data);
                $sortie[] = (object) ['op' => 'patch', 'kind' => $kind, 'id' => $data->id, 'data' => $data];
                continue;
            }
            if ($kind === 'prise') {
                // deux appareils peuvent ajouter une prise au meme plan en meme temps :
                // le serveur tranche sur le numero
                $freres = [];
                foreach ($db->prises as $p) {
                    if (($p->planId ?? null) === ($data->planId ?? null)) {
                        $freres[] = $p;
                    }
                }
                $pris = [];
                $max = 0;
                foreach ($freres as $p) {
                    $pris[] = $p->n ?? null;
                    $max = max($max, (int) ($p->n ?? 0));
                }
                if (!is_int($data->n ?? null) || in_array($data->n, $pris, true)) {
                    $data->n = $freres ? $max + 1 : 1;
                }
            }
            // position d'un plan : apres tel plan, ou en tete ('' = avant tous)
            $apres = property_exists($op, 'apres') ? $op->apres : null;
            if ($kind === 'plan' && $apres !== null) {
                array_splice($db->plans, place_apres($db->plans, $apres), 0, [$data]);
            } else {
                $db->{$c}[] = $data;
            }
            $res = (object) ['op' => 'add', 'kind' => $kind, 'data' => $data];
            if ($kind === 'plan' && $apres !== null) {
                $res->apres = $apres;
            }
            $sortie[] = $res;
        } elseif ($t === 'del') {
            $id = $op->id ?? null;
            $c = collection($db, $kind);
            if ($c === null || !$id) {
                continue;
            }
            $avant = count($db->$c);
            $db->$c = array_values(array_filter($db->$c, function ($e) use ($id) {
                return ($e->id ?? null) !== $id;
            }));
            if (count($db->$c) === $avant) {
                continue;
            }
            $sortie[] = (object) ['op' => 'del', 'kind' => $kind, 'id' => $id];
            if ($kind === 'plan') {
                $restent = [];
                foreach ($db->prises as $p) {
                    if (($p->planId ?? null) === $id) {
                        $sortie[] = (object) ['op' => 'del', 'kind' => 'prise', 'id' => $p->id ?? null];
                    } else {
                        $restent[] = $p;
                    }
                }
                $db->prises = $restent;
            }
            if ($kind === 'prise' && !empty($op->planId)) {
                $freres = [];
                foreach ($db->prises as $p) {
                    if (($p->planId ?? null) === $op->planId) {
                        $freres[] = $p;
                    }
                }
                usort($freres, function ($a, $b) {
                    return (int) ($a->n ?? 0) - (int) ($b->n ?? 0);
                });
                foreach ($freres as $i => $p) {
                    if (($p->n ?? null) !== $i + 1) {
                        $p->n = $i + 1;
                        $sortie[] = (object) ['op' => 'patch', 'kind' => 'prise', 'id' => $p->id, 'data' => (object) ['n' => $i + 1]];
                    }
                }
            }
        } elseif ($t === 'move') {
            // un plan change de place : juste apres tel plan, ou en tete ('' = avant tous)
            $id = $op->id ?? null;
            $apres = property_exists($op, 'apres') ? $op->apres : '';
            if ($kind !== 'plan' || !$id || $id === $apres) {
                continue;
            }
            $bouge = trouver($db, 'plan', $id);
            if ($bouge === null) {
                continue;
            }
            $db->plans = array_values(array_filter($db->plans, function ($p) use ($id) {
                return ($p->id ?? null) !== $id;
            }));
            array_splice($db->plans, place_apres($db->plans, $apres), 0, [$bouge]);
            $sortie[] = (object) ['op' => 'move', 'kind' => 'plan', 'id' => $id, 'apres' => $apres];
        } elseif ($t === 'optiques') {
            $liste = $op->liste ?? null;
            if (is_array($liste)) {
                $db->optiques = array_map('strval', $liste);
                $sortie[] = (object) ['op' => 'optiques', 'liste' => $db->optiques];
            }
        }
    }
    return $sortie;
}
