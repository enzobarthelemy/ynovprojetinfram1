* Titre : ADR 001 - Choix de la stratégie de déploiement IaC

* Contexte : Obligation de déployer l'infrastructure via code IaC, nécessite le choix de la stratégie (CloudFormation? CDK ?)

* Décision : Utilisation d'une stratégie IaC en CDK avec le langage Python car CDK majoritairement utilisé dans les environnements de PRODUCTION, et Python pour une meilleure lisibilité/compréhension du code

* Conséquences :
	- Création d'une structure de fichiers CDK Python lisible :
		- Création d'un fichier principal app.py
		- Création de plusieurs fichiers secondaires : vpc_stack.py, sg_stack.py, alb_stack.py, s3_stack.py, asg_stack.py, ec2_stack.py, rds_stack.py
	- Le fichier principal dépend des fichiers secondaires
	- La répartition en fichiers secondaires permet de répartir facilement le travail entre les collaborateurs tout en distinguant rapidement quel fichier gère quel type d'instance/configuration