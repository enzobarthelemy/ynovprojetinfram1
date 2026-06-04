* Titre : ADR 002 - Choix de l'instance de base de données

* Contexte : L'application Wordpress nécessite une base de données qui, selon les demandes reçues, doit être externalisé des serveurs web. Il est donc nécessaire de choisir quel instance AWS portera la charge des données Wordpress

* Décision : Utilisation d'AWS RDS sous MySQL 8.0 (moteur 100% compatible et recommandé par Wordpress). Le mot de passe master est généré et géré automatiquement par RDS (manage_master_user_password) afin qu'aucun mot de passe ne soit en clair dans le template CloudFormation. La résilience cross-région est assurée par snapshot + copie cross-région (la read-replica cross-région étant bloquée sur AWS Academy).

* Conséquences :
	- Création d'une base AWS RDS sous MySQL 8.0, mot de passe master géré par RDS (secret Secrets Manager rds!db-...)
	- Création d'un secret pour l'utilisateur applicatif Wordpress (moindre privilège)
	- Utilisation de ce secret sur les instances Wordpress pour s'authentifier sur la base
	- DR cross-région par snapshot horaire copié vers us-west-2 (restauration d'une base au failover)