** AWS RUNBOOK : Maintenance Docker Wordpress - EC2 **

1. Informations générales
-------------------------
	* ID : RB-AWS-003
	* Version : 1.0
	* Auteur/Équipe : Enzo BARTHELEMY, équipe infra
	* Description : Permet de mettre à jour le nombre d'instances minimales et/ou maximales exécutées par ASG sur AWS
	
	** Point d'attention : Les EC2 étant géré par ASG, lui même géré par CDK, toute modification de configuration sur Docker ne sera pas refaite en cas de redéploiement d'instance. Il est nécessaire de modifier le fichier asg.py & user_data.sh pour que cela soit permanent. **
	
2. Prérequis AWS et accès
-------------------------
	* Région AWS nominale : us-east-1
	* Région AWS secours : us-west-2
	* Rôle/Permissions IAM : Rôle "LabRole", accès en modification sur ASG, accès aux instances EC2 par SSM Session Manager
	* Outils requis :
		- Console web AWS

3. Environnement & ressources cibles
------------------------------------
	* Nom du Stack CDK : InfraPrimaryStack ou InfraSecondaryStack (selon le périmètre d'action souhaité)
	* Nom des ressources concernées :
		- US-EAST-1 EC2 "wordpress-asg-primary"
		- US-WEST-2 EC2 "wordpress-asg-secondary"
		
4. Procédure étape par étape
----------------------------
	1- Vérification de l'état initial des instances
		1: Se connecter sur la console AWS
		2: Accéder au panel EC2
		3: Vérifier le nombre d'instances actives
	
	Résultat attendu : 2 instances actives par défaut
	
		4: Accéder à la page "Groupes Auto Scaling"
	
	Résultat attendu : Infra<Primary|Secondary>Stack-AsgNestedStackAsgNestedStackResource avec 2 ressources saines
	
	2- Vérification de Docker sur une instance EC2
		1: Sélectionner une instance EC2
		2: Cliquer sur Se connecter > SSM Session Manager > Se connecter
		3: Taper les commandes suivantes :
			- bash
			- sudo su ec2-user
			- (optionnel, pour passer en root) sudo su -
		4: Vérifier le statut du container Docker :
			- docker ps
		
		Résultat attendu : 1 container Docker "wordpress-wordpress-1" en Statut Healthy
		
	3- Actions de maintenance Docker
		- Pour stopper le container, taper "docker stop wordpress-wordpress-1"
		- Pour démarrer le container, taper "docker start wordpress-wordpress-1"
		- Pour exécuter des commandes dans le container, taper "docker exec -ti wordpress-wordpress-1 bash" (ouvre un terminal bash dans l'instance) puis taper les commandes souhaitées
	


5. Procédure de rollback en cas de problème suite à des actions de maintenance
------------------------------------------------------------------------------		
		* Option A : Localiser le problème et le résoudre
			1: Dans l'instance EC2, vérifier le statut du container : "docker ps -a"
			2: Essayer de démarrer le container : "docker start wordpress-wordpress-1"
			3: Vérifier les logs du container : "docker logs wordpress-wordpress-1"

			4: Si le problème ne parvient pas à être résolu, appliquer l'option B et prévenir d'administrateur en charge.
		
		* Option B : Forcer la recréation d'une nouvelle instance
			1: Depuis le panel EC2 sur la console AWS, résilier l'instance impactée
			2: Attendre le redéploiement d'une nouvelle instance par ASG
		
		Résultat attendu : Après quelques minutes, une nouvelle instance est déployée. ASG en statut 2/2 saine.