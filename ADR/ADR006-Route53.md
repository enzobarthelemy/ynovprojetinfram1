* Titre : ADR 006 - Route 53

* Contexte : L'infrastructure se doit d'être résiliente et évolutive selon les contraintes demandées : "aucune interruption de service ne sera tolérée"

* Décision : Utilisation de Route 53 pour la gestion des failovers au niveau du site web et de S3

* Conséquences :
	- Création d'une Zone hébergée Publique ynov-infram1-grp1.com
	- Association des ALB us-east-1 et us-west-2 sous le sous-domaine sub.ynov-infram1-grp1.com. us-east-1 est défini comme Primary et us-west-2 est défini comme Secondary
	- Création de HealthCheck pour les ALB us-east-1 et us-west-2
	- Création d'une Zone hébergée Privée ynov-infram1-grp1.intra
	- Association des S3 us-east-1 et us-west-2 sous le sous-domaine s3.ynov-infram1-grp1.intra. us-east-1 est défini comme Primary et us-west-2 est défini comme Secondary
	- Création de HealthCheck pour les S3 us-east-1 et us-west-2