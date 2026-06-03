** AWS PLAYBOOK : Réponse à l'incident "Déploiement en boucle d'instances EC2 **

1. Informations générales
-------------------------
	* ID : PB-AWS-001
	* Version : 1.0
	* Type d'incident : ASG instable, déploiement et résiliation d'EC2 en boucle
	* Description : Indisponibilité de l'application, renouvellement irrégulier d'instances EC2, ASG n'est pas dans un état Sain
	* Runbook associé : RB-AWS-003
	
2. Rôles et responsabilités
---------------------------
	* Incident Commander (IC) : Enzo BARTHELEMY
	* Ops/Tech Lead : Enzo BARTHELEMY
	* Communications : Enzo BARTHELEMY

3. Phase 1 : triage et vérification de l'alerte
-----------------------------------------------
	1- Vérification Amazon CloudWatch
		* Détection d'une hausse anormale de déploiement et de résiliation d'instances EC2 par ASG
	
	2- Impact
		* Failover Route 53 inopérant, les deux régions sont impactées
		* Toutes les instances EC2 des deux régions se font résilier et redéployer à tour de rôle sans arrêt
		* Page web inaccessible : erreur 5xx (Bad gateway ou Gateway Timeout)
		
4. Phase 2 : diagnostique et arbre de décision
----------------------------------------------
	1- Depuis la console web AWS, accéder au panel EC2
	2- Se connecter en SSM sur l'instance la plus récemment déployer
	3- Taper les commandes suivantes :
		- bash
		- sudo su ec2-user 
		- (optionnel, pour passer en root) sudo su -
	4- Vérifier le statut du container Docker : docker ps -a. Le statut n'est logiquement pas en Healthy, autrement ce Playbook ne répondra pas au problème.
	5- Vérifier les logs associés au container : docker logs wordpress-wordpress-1. Noter les erreurs présentes s'il y en a, puis passer à l'étape suivante.
	6- Vérifier le fichier docker-compose.yml : cat /opt/wordpress/docker-compose.yml. Si le fichier est présent et que toutes les valeurs sont bien renseignées, passer à l'étape suivante. Sinon, passer à la Phase 3 - Action 1.
	7- Vérifier le fichier de log du script user_data.sh : cat /var/log/user-data.log. Si le fichier s'est bien exécuté jusqu'au bout (message "===> User data terminé avec succès."), passer à l'étape suivante. Sinon, passer à la Phase 3 - Action 2.
	8- Vérifier le dossier de wordpress : ls /mnt/efs/wordpress. Si des fichiers Wordpress sont bien présent, passer à la Phase 3 - Action 3.

5. Phase 3 : actions de résolution (atténuation)
------------------------------------------------		
	* Action 1 : fichier docker-compose.yml incomplet ou inexistant
		1- Accéder au dossier : cd /opt/wordpress
		2- Créer le fichier : touch docker-compose.yml
		3- Alimenter le fichier en modifiant les variables par les valeurs réelles :
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
		4- Exécuter le container : docker compose up -dans
		5- Vérifier le statut du container : docker ps -accéder
		6- Vérifier les logs du container : docker logs wordpress-wordpress-1
		7- Si non résolu, soit passer à l'action suivante (si plusieurs erreurs étaient présentes ou si de nouvelles erreurs correspondent aux autres cas, soit passer à la Phase 4.
		
	* Action 2 : détection de l'erreur & tentative de résolution
		1- Tester si http://localhost répond au sein du container : docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T wordpress curl -sf http://localhost. Il est possible qu'aucun retour de soit fait dans le terminal
		2- Ouvrir le fichier user_data.sh originel
		3- Localiser la ligne ou le bloc de ligne ayant généré l'erreur
		4- Rechercher la raison de l'erreur et la résoudre
		5- Sauvegarder le script modifié et attendre la mise à jour de la Stack CDK
		6- Résilier toutes les instances EC2 encore présentes
		7- Se connecter sur la nouvelle instance créée par ASG en SSM
		8- Vérifier le fichier de logs du script : tail -f /var/log/user-data.log. S'il y a d'autres erreurs, reproduire les étapes précédentes. Si plus possible de résoudre, passer à la Phase 4.
		
	* Action 3 : montage du point /mnt/efs/wordpress
		1- Monter le partage efs : sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport <FQDN_EFS>:/ /mnt/efs/wordpress
		2- Vérifier le contenu du dossier : ls /mnt/efs/wordpress. Si des fichiers Wordpress sont présents, essayer de relancer le container. Autrement, passer à la Phase 4.

6. Phase 4 : procédure d'escalade
---------------------------------		
	Rassembler toutes les informations collectées pendant la Phase 2 et les transmettre à l'administrateur principal.

7. Phase 5 : post-incident
--------------------------
	1- Heure de début de l'incident :
	2- Heure de la résolution :
	3- Cause racine identifiée :
	4- Action préventive : Ajout d'alerte CloudWatch, notification des administrateurs en cas de non réponse du site web, revérification régulière des configurations et point d'attention en cas de mise à jour de la Stack CDK associée

