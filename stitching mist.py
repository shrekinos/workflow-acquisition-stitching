import re  # pour découpage des noms
import shutil # suppresion dossier temporaire
import subprocess # lancer mist en programme externe
from pathlib import Path # manipuler les directory
import tifffile # lecture fichiers tiff

import os # module pour intéragir avec l'OS de l'ordi dont les fichiers/dossiers
import tkinter as tk # module pour afficher des interfaces utilisateurs (GUI toolkit)
from tkinter import filedialog # importe truc pour gérer fenetre direction
from datetime import datetime  

#----------------------------------------------------------------------------------------------------------

### PARAMETRES (Plus tard: possibilité de créer des profils selon l'échantillon)

origine = "LR"                        # coin de départ de l'acquisition (lower right)
numerotation = "HORIZONTALCOMBING"    # acquisition "snake" ligne par ligne
chevauchement = 10                    # pourcentage de l'overlap d'acquisition

#----------------------------------------------------------------------------------------------------------

### RECUP CHEMINS DOSSIERS (phase test sans GUI complet)

root = tk.Tk()
root.withdraw()  # cache la fenêtre vide de tkinter, juste les fenetres de selection pr l'instant

choix_entree = filedialog.askdirectory(title="Choisissez le dossier contenant les tuiles")
choix_sortie = filedialog.askdirectory(title="Choisissez le dossier de sortie")
root.destroy()   # ferme  tkinter

# si pas de selection, arreter script
if not choix_entree or not choix_sortie:
    raise SystemExit("Sélection annulée.")

dossier_entree = Path(choix_entree)
dossier_parent_sortie = Path(choix_sortie)
# création dossier sortant:
dossier_sortie = dossier_parent_sortie / f"stitchingMIST_{datetime.now():%Y_%m_%d_%Hh%M}"

# Dossier temporaire pour les tuiles nettoyées (supprimé à la fin)
dossier_tif = dossier_sortie.parent / "tuiles_tif_temp"
dossier_tif.mkdir(parents=True, exist_ok=True) # créer le dossier et évite erreur si déjà existant

# Dossier temporaire pour les tuiles nettoyées (supprimé à la fin)
dossier_tif = dossier_sortie.parent / "tuiles_tif_temp"
dossier_tif.mkdir(parents=True, exist_ok=True) # créer le dossier et évite erreur si déjà existant


# __________
# (Pour plus tard GUI tkinter)
# def emplacement_dossier_entrant(dossier_entree):
#     chemin = filedialog.askdirectory(initialdir="/",title='Choisissez le dossier contenant les tuiles')

#     if chemin: #askdirectory renvoie un string et un string vide renvoie False donc on fait juste test booléen
#         # Mise à jour du chemin    
#         dossier_entree = chemin #modifier la valeur interne du stringvar, car un "=" ecrase l'objet stringvar

#         # # comptage des fichiers
#         # try:
#         #     fichiers = os.listdir(chemin)
#         #     compteur = len([ f for f in fichiers if os.path.isfile(os.path.join(chemin, f))])
#         #     affichage_compteur_var.set(compteur)
#         # except Exception as e:
#         #     print(f"Erreur: {e}")
#         #     affichage_compteur_var.set(0)

# # Fonction pour récup chemin dossier sortant
# def emplacement_dossier_sortant(dossier_sortant_var):
#     chemin = filedialog.askdirectory(initialdir="/",title='Choisissez un dossier sortant')
#     if chemin:
#         dossier_sortant_var = chemin
# __________


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
