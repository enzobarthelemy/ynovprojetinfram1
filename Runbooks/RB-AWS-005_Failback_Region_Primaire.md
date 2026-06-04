** AWS RUNBOOK : Déclencher le Failback (Retour à la normale) vers la région primaire **

1. Informations générales
-------------------------
	* ID : RB-AWS-005
	* Version : 1.0
	* Auteur/Équipe : Paul Hamon, Groupe Tiers classique et haute disponibilité
	* Description : Permet d'automatiser le rapatriement des données (base de données RDS et fichiers EFS) de la région de secours (us-west-2) vers la région primaire (us-east-1) avec un redéploiement dynamique via GitLab CI/CD.
	
	** Point d'attention : Cette opération de reprise s'effectue intégralement via l'Infrastructure as Code (IaC). Il ne faut pas recréer de ressources manuellement depuis la console AWS afin de ne pas désynchroniser l'état (state) de CloudFormation et GitLab. **
	
2. Prérequis AWS et accès
-------------------------
	* Région AWS nominale : us-east-1
	* Région AWS secours : us-west-2
	* Rôle/Permissions IAM : Droits d'exécution sur le projet GitLab (Maintainer/Owner)
	* Outils requis :
		- Interface web GitLab
		- Console web AWS

3. Environnement & ressources cibles
------------------------------------
	* Nom du Stack CDK : InfraPrimaryStack
	* Nom des ressources concernées :
		- Pipeline GitLab CI/CD (Jobs failback-rds et failback-efs)
		- US-EAST-1 Amazon RDS et EFS
		
4. Procédure étape par étape
----------------------------
	1- Vérification de l'état initial (pré-check)
		* Option A : console web AWS
			1: Choisir en haut à droite la région us-east-1
			2: Vérifier que les services sous-jacents d'AWS (VPC, EC2) sont de nouveau opérationnels suite à la panne.
			3: S'assurer que le site web est toujours accessible pour les utilisateurs (le trafic étant actuellement routé de manière transparente vers l'ALB en us-west-2).
		
		Résultat attendu : Site accessible et fonctionnel sur la région de secours.
		
	2- Exécution de l'action principale : Déclenchement de la pipeline
		* Option A : Interface web GitLab
			1: Se rendre sur le projet GitLab, dans Build > Pipelines
			2: Cliquer sur le bouton bleu "Run pipeline" (en haut à droite)
			3: Sélectionner la branche "main"
			4: Dans la section "Variables", ajouter une nouvelle variable avec Key : RUN_MODE et Value : failback
			5: Cliquer sur "Run pipeline"
			
		Résultat attendu : La pipeline se lance. Les jobs de déploiement classique sont ignorés au profit des jobs de reprise d'activité qui se mettent en attente d'action manuelle.
	
	3- Application du changement : Rapatriement des données
		* Étape 3.1 : Rapatriement de la base de données
			1: Sur la vue graphique de la pipeline GitLab, cliquer sur le bouton "Play" du job "failback-rds"
			
		Résultat attendu : Le script génère un snapshot de la base de secours, le copie vers la région primaire, restaure la base "wordpress-rds-failback" et met à jour les secrets de connexion. Le statut passe à "Passed".
			
		* Étape 3.2 : Rapatriement des fichiers EFS et redéploiement
			1: Une fois le job précédent terminé avec succès, cliquer sur le bouton "Play" du job "failback-efs"
			
		Résultat attendu : Le script inverse la réplication EFS, relance le déploiement CloudFormation primaire (qui monte automatiquement l'EFS rapatrié) et effectue un Instance Refresh de l'ASG. Le statut passe à "Passed".

	4- Validation (Post-check)
		* Option A : Console web AWS & Navigateur
			1: Aller sur Route 53 > Contrôles d'état (Health checks)
			2: Vérifier le statut du Health Check de l'ALB primaire (us-east-1)
			3: Ouvrir le nom de domaine du site WordPress dans un navigateur web
			
		Résultat attendu : Le Health Check est en statut "Sain" (Healthy). Le trafic est automatiquement rebasculé par Route 53 vers la côte Est. Le site s'affiche avec toutes les données ajoutées pendant la durée de la panne.

5. Procédure de rollback en cas d'échec
---------------------------------------		
		* En cas d'échec d'un des scripts GitLab (failback-rds ou failback-efs)
			1: Ne supprimer aucune ressource sur la région de secours (us-west-2).
			2: Lire les logs de l'erreur dans la console du job GitLab en échec.
			3: Si l'erreur est temporaire (ex: timeout API AWS), relancer simplement le job en échec via le bouton "Retry".
			4: Si l'erreur est structurelle, corriger le script .gitlab-ci.yml, pousser la modification avec Git et recommencer la procédure.
			5: Prévenir l'administrateur en charge.
				
		Résultat attendu : Le site web en production n'a subi aucune coupure grâce au routage Failover de Route 53 (qui maintient de force le trafic sur us-west-2 tant que l'infrastructure us-east-1 n'est pas 100% saine).