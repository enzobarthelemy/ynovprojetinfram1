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
- Alimentation du fichier vpc_stack.py, révision app.py et .gitlab-ci.yml + tests validés

** Thomas :
- Recherches techniques : Docker Wordpress, ALB
- Initialisation du dépôt gitlab https://gitlab.com/Mar-Thomasx/ynovprojetinfram1
- Mise en place CI/CD entre GitHub et GitLab pour déploiement automatisé sur AWS
- Création d'une structure python pour le déploiement par CDK (app.py + xxx_stack.py)
- Alimentation du fichier s3_stack.py, révision app.py et .gitlab-ci.yml + tests validés