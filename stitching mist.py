import re  # pour découpage des noms
import shutil # suppresion dossier temporaire
import subprocess # lancer mist en programme externe
from pathlib import Path # manipuler les directory
import tifffile # lecture fichiers tiff

#----------------------------------------------------------------------------------------------------------

### PARAMETRES (Plus tard: possibilité de créer des profils selon l'échantillon)
dossier_entree = Path("dossier entrant des tuiles") ### COMPLETER
dossier_sortie = Path("dossier sortant de stitching mist") ### COMPLETER
origine = "LR"                        # coin de départ de l'acquisition (lower right)
numerotation = "HORIZONTALCOMBING"    # acquisition "snake" ligne par ligne
chevauchement = 10                    # pourcentage de l'overlap d'acquisition

# Dossier temporaire pour les tuiles nettoyées (supprimé à la fin)
dossier_tif = dossier_sortie.parent / "tuiles_tif_temp"
dossier_tif.mkdir(parents=True, exist_ok=True) # créer le dossier et évite erreur si déjà existant

#----------------------------------------------------------------------------------------------------------

### ETAPE 1: nettoyer les tuiles
# explication du problème:
    # avec MIST plugin fiji: besoin de supprimer .ome du nom du fichier et ne conserver que .tif pour lecture des fichiers
    # avec mist-stitching python: un simple renommage conserve les métadonnées .ome et fausse la lecture des images
# ==> besoin de convertir totalement de .ome.tif à .tif

colonnes = []   # tous les numéros de colonne trouvés
lignes = []     # tous les numéros de ligne trouvés

# "*.ome.tif" ne prend que les images (surtout pour ignorer les .txt de métadonnées)
# !! ici remplacé par "*.tif" pour traiter les images renommées sans .ome mais qui ont toujours les métadonnées ome

for fichier in sorted(dossier_entree.glob("*.tif")):    # glob: lister fichiers  / sorted: ordre alphabétique

    # découpage du nom en 3 parties : nom - colonne _ ligne
    # exemple : "B_C3_puit_1_MMStack_Grid-1-" + "003" + "_" + "007" + ".ome.tif"

    m = re.fullmatch(r"(.+-)(\d+)_(\d+)\.tif", fichier.name)
    # m récupère le nom divisé en groupes (chaque "motif" entre parenthèse):
        # (.+-) tous les caractère du début jusqu'à un tiret - qui précède les numéro de grille
        # (\d+) : plusieurs chiffres séparés par "_"

    if m is None:
       continue    # ignorer les noms innatendus si autres images dans dossiers

    debut_nom, col, lig = m.group(1), m.group(2), m.group(3)

    # conversion de la grille de texte à entiers, et ajout à la liste
    colonnes.append(int(col))
    lignes.append(int(lig))

    # on lit l'image de CE fichier (page 0) et on la réécrit en .tif simple sans les métadonnées OME
    with tifffile.TiffFile(fichier) as tf:
        image = tf.pages[0].asarray() # page[0] = 1ere page = image contenue dans le fichier, sans la fiche ome après
    tifffile.imwrite(dossier_tif / (debut_nom + col + "_" + lig + ".tif"), image, metadata=None)

#----------------------------------------------------------------------------------------------------------

### ETAPE 2 : taille de la grille à partir des numéros trouvés

col_min, col_max = min(colonnes), max(colonnes)
lig_min, lig_max = min(lignes), max(lignes)
largeur = col_max - col_min + 1
hauteur = lig_max - lig_min + 1
print(f"{len(colonnes)} tuiles, grille de {largeur} colonnes x {hauteur} lignes")

# vérification si tuile manquante
if len(colonnes) != largeur * hauteur:
    raise SystemExit("Il manque des tuiles : le nombre ne correspond pas à la grille.")

# motif de nom pour MIST : "{ccc}" et "{rrr}" ont autant de lettres que de chiffres
motif = debut_nom + "{" + "c" * len(col) + "}_{" + "r" * len(lig) + "}.tif"

#----------------------------------------------------------------------------------------------------------

### ETAPE 3: mist stitching

commande = [
    # emplacement de l'installation mist-stitching (rendre dynamique??)
    "python", "mist_stitching/main.py", ### COMPLETER

    # dossier entrant et sortant
    "--image-dirpath", str(dossier_tif),
    "--output-dirpath", str(dossier_sortie),

    # taille de la grille (dynamique, cf etape2)
    "--grid-width", str(largeur),
    "--grid-height", str(hauteur),

    "--start-row", str(lig_min),
    "--start-col", str(col_min),

    # paramètre définis au début (pour créations de profils selon échantillon observé)
    "--filename-pattern", motif,
    "--filename-pattern-type", "ROWCOL",
    "--grid-origin", origine,
    "--numbering-pattern", numerotation,
    "--horizontal-overlap", str(chevauchement),
    "--vertical-overlap", str(chevauchement),

    "--save-image",
]

processus = subprocess.run(commande)

# supprimer les tuiles temporaires
shutil.rmtree(dossier_tif)

print("Succès" if processus.returncode == 0 else f"Échec (code {processus.returncode})")