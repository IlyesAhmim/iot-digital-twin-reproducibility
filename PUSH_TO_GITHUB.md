# Mettre ce dossier sur GitHub

Le dossier complet `GITHUB_READY` constitue la racine à versionner. Ne déplacer pas uniquement les scripts : conserver les dossiers voisins `results/` et `reports/`.

## Nouveau dépôt vide

Créer le dépôt voulu dans votre compte, puis, depuis `GITHUB_READY` :

```bash
git init -b main
git add .
git commit -m "Add manuscript reproducibility code and saved results"
git remote add origin URL_DE_VOTRE_DEPOT
git push -u origin main
```

Remplacer `URL_DE_VOTRE_DEPOT` par l'adresse réelle. Aucun identifiant ne doit être écrit dans les fichiers ; vous vous authentifierez vous-même si Git le demande.

## Dépôt existant

Cloner d'abord le dépôt existant dans un dossier séparé, puis copier le **contenu** de `GITHUB_READY` dans ce clone en conservant son dossier `.git`. Examiner `git status` et `git diff` avant de créer le commit. La nouvelle arborescence regroupe le moteur scientifique dans un sous-dossier : si votre dépôt contient déjà ces scripts à sa racine, vérifier les doublons et les liens du README avant publication. Ne pas faire de push forcé.

```bash
git status
git add .
git commit -m "Add revised reproducibility package and audit outputs"
git push
```

La licence, la version/tag et un éventuel DOI doivent être choisis par les auteurs ; rien n'a été inventé ou publié automatiquement. Les archives contiennent les résultats déjà calculés. Aucun résultat nouveau n'a été produit pour préparer ce dossier.
