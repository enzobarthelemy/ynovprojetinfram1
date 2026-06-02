# Journal de bord
# Projet Connect M1
---------------------------------------------------------------------------------------------------------

Sujet : 3-Tiers classique et haute disponibilité
Période : Du 29/05/2026 au 05/06/2026
Composition du groupe :
	- Enzo BARTHELEMY
	- Thomas MARCILLY
	- Paul HAMON


---------------------------------------------------------------------------------------------------------
### Jour 1 : 29/05/2026 - Objectif : découverte du sujet & conception d'une V1 de l'infrastructure

** Travail en commun :
- Sélection et découverte du sujet
- Analyse du sujet
- Recueil des besoins et des contraines
- Projection d'une première version de l'infrastructure
- Sélection de la stratégie IaC : CDK Python
- Préparation des outils de travail

** Paul :
- Conception d'un premier jet du plan d'architecture
- Conception du schéma des flux

** Enzo :
- Initialisation du dépôt git https://github.com/enzobarthelemy/ynovprojetinfram1
- Création et alimentation du journal de bord "journaldebord.md"
- Création et alimentation du fichier de choix du sujet "Sujet.md"
- Recherches techniques : Docker Wordpress & WooCommerce, interconnexion avec les instances S3 et RDS
- Alimentation du fichier vpc_stack.py, révision app.py et .gitlab-ci.yml + test individuel OK

** Thomas :
- Recherches techniques : Docker Wordpress, ALB
- Initialisation du dépôt gitlab https://gitlab.com/Mar-Thomasx/ynovprojetinfram1
- Mise en place CI/CD entre GitHub et GitLab pour déploiement automatisé sur AWS
- Création d'une structure python pour le déploiement par CDK (app.py + xxx_stack.py)
- Alimentation du fichier s3_stack.py, révision app.py et .gitlab-ci.yml + test individuel OK
- Merge des configs réalisées


---------------------------------------------------------------------------------------------------------
### Jour 2 : 01/06/2026 - Objectif : poursuite de la confection des fichiers .py & début des documentations écrites

** Travail en commun :
- Validation de l'architecture cible et des plans associés
- Recherches techniques sur le failover global inter-vpc : approfondissement ultérieurement
- Préparation questions pour prochaine intervention formateur :
	- Réplicat RDS bloquée sur autre région. Alternative ?
	- Playbook ?
	- Implémentations supplémentaires si on a le temps : WAF ?
- Debug merge des configs & test de déploiement globale de l'infrastructure

** Paul :
- Alimentation du fichier alb_stack.py + test individuel OK
- Création RB-AWS-001 : Ajout/Modif de ports sur ALB

** Enzo :
- Rédaction des ADR001, ADR002, ADR003
- Alimentation du fichier asg_stack.py
- Recherches techniques réplicat Wordpress : utilisation EFS recommandée + réplicat RDS + réplicat secrets
- Création et alimentation du fichier efs_stack.py + user_data.sh
- Modification du fichier sg_stack.py, révision .gitlab-ci.yml
- Création RB-AWS-002 : Modif du nombre d'instances déployées avec ASG
- Modification user_data.sh -> modification dnf par yum

** Thomas :
- Alimentation du fichier sg_stack.py, révision .gitlab-ci.yml + test individuel OK
- Recherches techniques réplicat Wordpress : utilisation EFS recommandée + réplicat RDS + réplicat secrets
- Alimentation du fichier rds_stack.py, révision .gitlab-ci.yml + test individuel OK
- Merge des configs réalisées, remise en ordre des déploiements + test global = déploiement opérationnel : https://gitlab.com/Mar-Thomasx/ynovprojetinfram1/-/pipelines/2567342149 mais problèmes réseaux sur EC2
- Révision du réplicat RDS : restriction lab AWS empêchant le réplicat de la base entre région


*** ACTIONS POUR DEMAIN : 
	- Modifier vpc_stack.py et sg_stack.py pour résoudre les problèmes d'accès à Internet & BDD des EC2 :
		- Ajout NAT GATEWAY -> vpc_stack.py
		- Association sur les routes -> vpc_stack.py
		- Création d'une règle sortante 0.0.0.0/0 sur les SG -> sg_stack.py
		- Création d'une règle sortante 3306 vers SG BDD -> sg_stack.py
	- Approfondir les tests du user_data.sh. Dernier résultat : Docker UP mais unhealthy


---------------------------------------------------------------------------------------------------------
### Jour 3 : 02/06/2026 - Objectif : correction des erreurs d'hier & test de l'infrastructure complète

** Travail en commun :
- Réponses aux questions (formateur) :
	- Playbook ? Imaginer des scénarios et (si possible et si le temps) les reproduire
	- WAF ? si on veut
	- Blocage RDS inter-région ? Proposer une solution alternative pour la démo, et noter dans un cas de PROD comment faire
	- Etudier Route 53 pour la bascule inter-région + voir stratégie de bascule (actif/actif vraiment nécessaire ? Mettre en place un stratégie d'allumage des VMs en cas de bascule ?) --> vu par Enzo/Paul
	- Etudier les configs IAM qu'on aurait dû faire (hors AWS Academy)
	- Revoir les stacks CloudFormation pour n'en avoir qu'un seul au lieu d'un stack par type d'instance --> vu par Thomas
	- Mettre à jour le schéma d'architecture (nat gateway, sg, route 53) --> vu par Paul
	- Annulation de la contrainte Docker (on peut retirer si complication)

** Paul :
- Correction vpc_stack.py : Création NAT GATEWAY, association sur les tables de routage PrivateWeb
- Clone infrastructure sur autre instance AWS
- Mise à jour du schéma d'architecture
- Recherches stratégie de bascule/gestion des instances Backup

** Enzo :
- Clone infrastructure sur autre instance AWS
- Test du script user_data.sh sur environnement de test : accessible depuis l'extérieur, BDD HS -> installation non finalisée
- Debug user_data.sh + test individuel OK sur région principale, site opérationnel
- Debug ec2 région secondaire : pb de droits, maj user_data.sh pour vérification des droits des fichiers avant modification
- Recherches et tests Route 53 : création bascule DNS avec domaine de test OK
- Création route53.py et adaptation des autres fichiers

** Thomas :
- Correction sg_stack.py : ajout des règles sortantes sur SgWeb
- Merge correction sg_stack.py et vpc_stack.py + test OK
- Modification rds_stack.py : configuration nom bdd
- Reconfig CDK : rassemblement des CloudFormation sur un seul stack + test déploiement global OK
- Merge des configs réalisées + test global : revoir config route53.py (mauvaise config DNS A), revoir config user_data.sh (mauvaise config URL Wordpress), revoir config EFS répliqué Read-Only sur 2e région


*** ACTIONS POUR DEMAIN : 
	- Revoir efs.py : réappliquer la config de réplication Read-Only sur la 2e région (Wordpress n'a pas besoin d'écrire pour la 2e région car pas de traffic dessus sauf si incident)
	- Revoir HealthCheck Route 53 ?
	- Point plan d'architecture v2
	- Etude des configs IAM qu'on aurait du faire dans un contexte de PROD		


---------------------------------------------------------------------------------------------------------
### Jour 4 : 03/06/2026 - Objectif : correction des erreurs d'hier & test de l'infrastructure complète
