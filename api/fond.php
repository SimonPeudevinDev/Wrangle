<?php
// Les plans de decor importes : un fichier chacun dans donnees/fonds, nomme
// d'apres son contenu ; le projet n'en garde que le nom (« fond:… »). Une image
// n'est ainsi qu'une fois chez l'hebergeur, et ni les espaces ni les
// sauvegardes ne la recopient.
//   POST { data: "data:image/webp;base64,…" }  -> { f }
//   GET  ?f=…                                  -> l'image, gardee en cache (elle ne change jamais)
require __DIR__ . '/commun.php';
define('FONDS', DONNEES . '/fonds');
$TYPES = ['image/webp' => 'webp', 'image/jpeg' => 'jpg', 'image/png' => 'png'];

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
    $nom = (string) ($_GET['f'] ?? '');
    $f = FONDS . '/' . $nom;
    if (!preg_match('/^[0-9a-f]{20}\.(webp|jpg|png)$/', $nom, $m) || !is_file($f)) {
        repondre(404, ['erreur' => 'introuvable']);
    }
    header('Content-Type: ' . array_search($m[1], $TYPES));
    header('Cache-Control: public, max-age=31536000, immutable');
    header('Content-Length: ' . filesize($f));
    readfile($f);
    exit;
}

$c = corps();
if ($c === null || !preg_match('#^data:(image/(?:webp|jpeg|png));base64,(.+)$#s', (string) ($c->data ?? ''), $m)) {
    repondre(400, ['erreur' => 'image attendue (WebP, JPEG ou PNG)']);
}
$octets = base64_decode($m[2], true);
if ($octets === false || $octets === '' || strlen($octets) > 4 * 1024 * 1024) {
    repondre(400, ['erreur' => 'image illisible ou de plus de 4 Mo']);
}
$nom = substr(sha1($octets), 0, 20) . '.' . $TYPES[$m[1]];
if (!is_dir(FONDS)) {
    mkdir(FONDS, 0755, true);
}
if (!is_file(FONDS . '/' . $nom)) {
    file_put_contents(FONDS . '/' . $nom, $octets, LOCK_EX);
}
repondre(200, ['f' => $nom]);
