* Titre : ADR 002 - Choix de l'instance de base de données

* Contexte : L'application Wordpress nécessite une base de données qui, selon les demandes reçues, doit être externalisé des serveurs web. Il est donc nécessaire de choisir quel instance AWS portera la charge des données Wordpress

* Décision : Utilisation d'AWS RDS sous MariaDB car utilisation d'un moteur 100% compatible et recommandé par Wordpress + sauvegarde/réplication/redondance configurable efficacement

* Conséquences :
	- Création d'une base AWS RDS sous MariaDB
	- Création de secrets pour s'authentifier sur la base
	- Utilisation des secrets sur les instances Wordpress pour s'authentifier sur la base