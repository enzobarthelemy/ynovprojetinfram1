# Table des matières
I- Informations générales
II- Prérequis AWS & accès
III- Environnement & ressources cibles
IV- Procédure étape par étape
A. Étape 1 : Vérification de l'état initial (pré-check)
B. Étape 2 : Exécution de l'action principale (Déclenchement de la bascule)
C. Étape 3 : Application du changement (Promotion de l'environnement)
D. Étape 4 : Validation (Post-check)
V- Procédure de rollback (en cas d'échec)

## I- Informations générales
ID du Runbook: RB-AWS-006
Version : 1.0 
Auteur / Équipe: Paul Hamon / Groupe Tiers classique et haute disponibilité 
Description: Ce runbook décrit la procédure de "Failover" (Bascule d'urgence) vers la région de secours (us-west-2) suite à la perte de la région primaire (us-east-1). Il déclenche la promotion du système de fichiers EFS en mode lecture/écriture et rafraîchit les serveurs de secours pour qu'ils prennent le relais complet de la production.
NB : La bascule réseau (DNS) est gérée de manière totalement automatique par AWS Route 53. Ce runbook ne concerne que l'activation des écritures sur le stockage.

## II- Prérequis AWS & accès
Pour exécuter ce runbook, vous devez disposer des éléments suivants :
Région AWS nominale : us-east-1 (N. Virginia)
Région AWS secours : us-west-2 (Oregon)
Rôle / Permissions IAM: Droits d'exécution sur le projet GitLab (Maintainer/Owner) pour déclencher la pipeline.
Outils requis: Interface web GitLab (CI/CD) et Console web AWS (pour la supervision).

## III- Environnement & ressources cibles
Identifiez précisément les ressources sur lesquelles vous allez agir :
Nom du Stack CloudFormation : InfraSecondaryStack
ID/Nom de la ressource principale : Pipeline GitLab CI/CD (Job `failover`) et ressources US-WEST-2 (EFS, Auto Scaling Group).

## IV- Procédure étape par étape

### A. Étape 1 : Vérification de l'état initial (pré-check)
Confirmez qu'un incident majeur (Crash d'AZ, panne régionale AWS) affecte la région Est.
1. Allez sur la console AWS > Route 53 > Contrôles d'état (Health checks).
2. Vérifiez que le Health Check primaire (us-east-1) est en statut "Unhealthy".
3. Vérifiez que Route 53 a bien basculé le trafic : le site web doit afficher une page d'erreur (car la base de secours fonctionne en lecture, mais l'EFS de secours est toujours verrouillé en lecture seule).

### B. Étape 2 : Exécution de l'action principale (Déclenchement de la bascule)
1. Se rendre sur le projet GitLab, dans Build > Pipelines.
2. Cliquez sur le bouton bleu "Run pipeline" (en haut à droite).
3. Sélectionnez la branche "main".
4. Dans la section "Variables", ajoutez une nouvelle variable avec Key : `RUN_MODE` et Value : `failover`.
5. Cliquez sur "Run pipeline".

### C. Étape 3 : Application du changement (Promotion de l'environnement)
Contrairement à un déploiement classique, l'architecture "Warm Standby" permet une reprise très rapide.
1. Sur la vue graphique de la pipeline GitLab, cliquez sur le bouton "Play" du job manuel `failover`.
Attendu : Le job s'exécute avec succès. En arrière-plan, le script supprime la configuration de réplication EFS (ce qui promeut immédiatement le disque de l'Oregon en mode "Writable"), puis lance un "Instance Refresh" sur l'Auto Scaling Group de l'Oregon. Les serveurs EC2 redémarrent pour monter le disque avec les droits d'écriture.

### D. Étape 4 : Validation (Post-check)
1. Ouvrez le nom de domaine du site WordPress dans un navigateur web.
2. Connectez-vous à l'interface d'administration WordPress (/wp-admin).
3. Tentez de téléverser (upload) une nouvelle image dans la bibliothèque de médias.
Attendu : Le site charge rapidement. L'upload de l'image réussit, confirmant que l'EFS secondaire est bien inscriptible et que la base de données secondaire (`wordpress-rds-secondary`) encaisse bien les nouvelles requêtes. La production a repris.

## V- Procédure de rollback (en cas d'échec)
L'environnement principal (Est) étant déjà en panne, le risque d'aggraver la situation sur l'Ouest est faible.
Si le script GitLab `failover` échoue (ex: API AWS indisponible) :
1. Relancez le job GitLab via le bouton "Retry".
2. Si le script échoue systématiquement lors de la promotion EFS, exécutez la commande d'urgence de contournement via l'AWS CLI (si configurée localement) : 
`aws efs delete-replication-configuration --source-file-system-id [ID_DU_FS_EST] --region us-east-1`
3. Si le problème persiste, prévenez immédiatement l'architecte Cloud de l'équipe (Niveau 3).

Une fois la région Est (us-east-1) réparée par les équipes d'AWS, n'effectuez aucune action manuelle de retour. Référez-vous au document **RB-AWS-005_Failback_Region_Primaire.md** pour rapatrier les données automatiquement.