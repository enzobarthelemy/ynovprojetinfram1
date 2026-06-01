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
- Merge des configs réalisées, remise en ordre des déploiements + test global = déploiement opérationnel : https://gitlab.com/Mar-Thomasx/ynovprojetinfram1/-/pipelines/2567342149 mais problème d'accès Internet sur les EC2
- Révision du réplicat RDS : restriction lab AWS empêchant le réplicat de la base entre région

*** ACTIONS POUR DEMAIN : modifier vpc_stack.py et sg_stack.py pour résoudre les problèmes d'accès à Internet des EC2 = ajout NAT GATEWAY, association sur les routes, création d'une règle sortantes 0.0.0.0/0 sur les SG