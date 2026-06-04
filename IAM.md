** Analyse des rôles IAM requis en contexte PRODUCTION **

À cause de l'environnement AWS Academy, nous sommes restreint au rôle LabRole et ne pouvons pas en créer d'autres; ce qui est une mauvaise pratique en condition réelle, surtout au vue des droits accordés par LabRole.
Voici le résultat de nos recherches pour les rôles principaux qui auraient dû être créés :

	* role-wordpress-ec2 - Pour EC2/ASG
		- Trusted Entity : ec2.amazonaws.com
		- Permissions accordées : 
				- Monter et lire/écrire sur l'EFS
				- Lire les Secrets
				- Écrire dans les logs CloudWatch
				- Accéder au Bucket S3 de sa propre région uniquement
				- Connexion uniquement via SSM Session Manager
		- Ressources : * (toutes les instances EC2)
			
			
	* role-backup-efs - Pour la notion de backup de l'EFS
		- Trusted Entity : backup.amazonaws.com
		- Permissions accordées :
				- Sauvegarder l'EFS généré
				- Lire les fichiers de l'EFS généré
				- Copier vers le vault de la 2e région
		- Ressources :
				- EFS généré par CDK
				- Backup Vault de la 1ère région
				- Backup Vault de la 2e région
	

	* role-s3-crr - Pour la réplication S3
		- Trusted Entity : s3.amazonaws.com
		- Permissions accordées :
				- Récupérer les configurations de réplication du Bucket
				- Récupérer les versions d'objets