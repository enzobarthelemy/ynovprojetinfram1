** Contraintes rencontrées **

1- Réplication RDS :
	Difficulté : Nous sommes contraints par l'environnement AWS Academy sur la réplication RDS d'une région à l'autre (Secondary en Read-Only). De ce fait, nous ne sommes pas en mesure de mettre en place un failover
				 propre entre les deux régions us-east-1 et us-west-2.
	Alternative Projet : Nous exécutons manuellement un job de backup puis de restauration de la base RDS sur la région secondaire, en recréant la base RDS avec la version à jour. De plus, les instances EC2 de la
						 région sont toutes résilées et recréées par ASG avec la nouvelle base. Le docker-compose.yml gérant la variable DB_HOST de Wordpress, aucune modification n'est à faire côté Wordpress.
	Solution en PRODUCTION : L'idéal est de créer un réplicat en Read-Only sur la 2e région, puis de créer un FQDN privé avec Route 53 et des HealthCheck pour vérifier que les RDS soient bien UP. En cas de non réponse,
							 un script Lambda passerait le RDS de la 2e région en principal et modifierait l'entrée associé au FQDN sur Route 53 pour y renseigner la nouvelle base. Aucun redéploiement des EC2 ne serait
							 à réaliser.
							 
2- Rôles IAM
	Difficulté : L'environnement AWS Academy empêche la création de nouveaux rôles IAM selon les usages dont nous aurions eu besoin.
	Alternative Projet : Utilisation du rôle LabRole fourni par AWS Academy.
	Solution en PRODUCTION : Création de rôles IAM avec le principe du moindre privilège pour les instances et les actions réalisées entre les types d'instances.
	
3- Failover S3
	Difficulté : Nous souhaitions mettre en place une solution de bascule automatique du S3 primaire vers le S3 secondaire afin d'avoir une configuration fixe côté Wordpress. Cependant, à cause de l'environnement AWS Academy
				 et de la configuration du plugin Wordpress, une bascule automatique ne sera pas possible.
	Alternative Projet : Modification de la configuration du plugin manuellement après bascule sur la région secondaire.
	Solution en PRODUCTION : Configuration d'un CloudFront regroupant les deux buckets S3. Cela permettra l'affichage des fichiers peut importe la région active, cependant une action manuelle est tout de même nécessaire
							 sur la configuration du plugin car on ne peut que renseigner un bucket et non pas un FQDN. De ce fait, sans action en cas de failover, les fichiers pourraient être lus et accessibles, mais
							 il serait impossible d'uploader de nouveaux médias.