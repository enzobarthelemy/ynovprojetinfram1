* Titre : ADR 004 - Utilisation de Docker et d'une image Wordpress sur les instances EC2

* Contexte : Possibilité d'exécuter Wordpress dans un container Docker. Le plugin WooCommerce doit également être installé

* Décision : Création d'un docker-compose.yml récupérant toutes les informations nécessaires pour l'installation du container (image Wordpress, image WP-CLI, secrets pour RDS, secrets pour Wordpress

* Conséquences :
	- Génération du docker-compose.yml dans le fichier user_data.sh
	- Fichier variabilisé pour s'adapter à son environnement (primary ou secondary)
		services:
			wordpress:
				image: wordpress:latest
				restart: always
				ports:
				- "80:80"
				environment:
				WORDPRESS_DB_HOST: "${DB_HOST}:${DB_PORT}"
				WORDPRESS_DB_NAME: "${DB_NAME}"
				WORDPRESS_DB_USER: "${DB_USER}"
				WORDPRESS_DB_PASSWORD: "${DB_PASS}"
				WORDPRESS_TABLE_PREFIX: "wp_"
				volumes:
				# Bind mount EFS — tous les fichiers WP vivent sur EFS, pas sur l'instance
				- ${EFS_MOUNT}:/var/www/html
				healthcheck:
				test: ["CMD", "curl", "-f", "http://localhost"]
				interval: 30s
				timeout: 10s
				retries: 5
				start_period: 60s

			# Service WP-CLI dedie (UID 33 = www-data, respecte les droits EFS)
			wp-cli:
				image: wordpress:cli
				volumes:
				- ${EFS_MOUNT}:/var/www/html
				environment:
				WORDPRESS_DB_HOST: "${DB_HOST}:${DB_PORT}"
				WORDPRESS_DB_NAME: "${DB_NAME}"
				WORDPRESS_DB_USER: "${DB_USER}"
				WORDPRESS_DB_PASSWORD: "${DB_PASS}"
				WP_CLI_CACHE_DIR: "/tmp/.wp-cli-cache"
				HOME: "/tmp"
				user: "33:33"