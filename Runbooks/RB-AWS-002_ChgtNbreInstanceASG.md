** AWS RUNBOOK : Modifier le nombre d'instances min/max sur ASG **

1. Informations générales
-------------------------
	* ID : RB-AWS-002
	* Version : 1.0
	* Auteur/Équipe : Enzo BARTHELEMY, équipe infra
	* Description : Permet de mettre à jour le nombre d'instances minimales et/ou maximales exécutées par ASG sur AWS
	
	** Point d'attention : ASG étant géré par CDK, il est nécessaire de faire cette modification dans le fichier asg_stack.py afin qu'elle soit permanente. Autrement elle sera supprimée au prochain déploiement CDK.**
	
2. Prérequis AWS et accès
-------------------------
	* Région AWS nominale : us-east-1
	* Région AWS secours : us-west-2
	* Rôle/Permissions IAM : Rôle "LabRole", accès en modification sur ASG
	* Outils requis :
		- Console web AWS
		- AWS CLI

3. Environnement & ressources cibles
------------------------------------
	* Nom du Stack CDK : asg_stack.py
	* Nom des ressources concernées :
		- US-EAST-1 Auto Scaling Group PrimaryASG
		- US-WEST-2 Auto Scaling Group SecondaryASG
		
4. Procédure étape par étape
----------------------------
	1- Vérification de l'état initial
		* Option A : console web AWS
			1: Choisir en haut à droite la région à vérifier : us-east-1 ou us-west-2
			2: Aller sur EC2 > Groupe Auto Scaling
			3: Vérifier "l'état de santé de l'instance"
		
		Résultat attendu : 2/2 Saine
		
		* Option B : AWS CLI
			1: Ouvrir son terminal et se connecter au compte AWS avec "aws configure" (ne pas refaire si déjà connecté)
			2: Exécuter : aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "NomASG" --query "AutoScalingGroups[*].Instances[*].{InstanceId:InstanceId, HealthStatus:HealthStatus, LifecycleState:LifecycleState}" --output table --region <NomRegion>
			
		Résultat attendu : Tableau avec 2 instances, colonne HealthStatus en "Healthy"
	
	2- Modification du nombre d'instances minimales/maximales
		* Option A : console web AWS
			1: Sélectionner l'ASG
			2: Cliquer sur Modifier à droite de l'écran, à côté du texte "Présentation de la capacité"
			3: Modifier la capacité minimale/maximale
			4: Modifier la capacité souhaitée pour la mettre à l'identique que la capacité minimale (si modifiée)
			5: Cliquer sur Mettre à jour
				
		Résultat attendu : Statut en "Mise à jour de la capacité". Après quelques minutes, le statut est "à la capacité souhaitée"
		
		* Option B : AWS CLI
			1: Pour modifier la capacité minimale, exécuter : aws autoscaling update-auto-scaling-group --auto-scaling-group-name "NomASG" --min-size <Valeur> --desired-capacity <Valeur>
			2: Pour modifier la capacité maximale, exécuter : aws autoscaling update-auto-scaling-group --auto-scaling-group-name "NomASG" --max-size <Valeur>
			3: Vérifier : aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "NomASG" --query "AutoScalingGroups[*].{Nom:AutoScalingGroupName, Min:MinSize, Desired:DesiredCapacity, Max:MaxSize}" --output table --region <NomRegion>
		
		Résultat attendu : Colonnes Desired, Max et Min avec les nouvelles valeurs
			
			4: Vérification statut global : aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "NomASG" --query "AutoScalingGroups[*].Instances[*].{InstanceId:InstanceId, HealthStatus:HealthStatus, LifecycleState:LifecycleState}" --output table
			
		Résultat attendu : Tableau avec le nombre d'instances correspondant, colonne HealthStatus en "Healthy"

5. Procédure de rollback en cas d'échec
---------------------------------------		
		* Option A : console web AWS
			1: Sélectionner l'ASG
			2: Cliquer sur Modifier à droite de l'écran, à côté du texte "Présentation de la capacité"
			3: Modifier la capacité minimale/maximale à la valeur antérieure
			4: Modifier la capacité souhaitée pour la mettre à l'identique que la capacité minimale (si modifiée)
			5: Cliquer sur Mettre à jour
				
		Résultat attendu : Statut en "Mise à jour de la capacité". Après quelques minutes, le statut est "à la capacité souhaitée". Les instances en trop sont en cours de résiliation.
		
			6: Prévenir l'administrateur en charge.
		
		* Option B : AWS CLI
			1: Remettre la capacité minimale antérieure avec la commande : aws autoscaling update-auto-scaling-group --auto-scaling-group-name "NomASG" --min-size <Valeur> --desired-capacity <Valeur> --region <NomRegion>
			2: Remettre la capacité maximale antérieure avec la commande : aws autoscaling update-auto-scaling-group --auto-scaling-group-name "NomASG" --max-size <Valeur> --region <NomRegion>
			3: Vérifier : aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "NomASG" --query "AutoScalingGroups[*].{Nom:AutoScalingGroupName, Min:MinSize, Desired:DesiredCapacity, Max:MaxSize}" --output table
		
		Résultat attendu : Colonnes Desired, Max et Min avec les valeurs antérieures
			
			4: Vérification statut global : aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "NomASG" --query "AutoScalingGroups[*].Instances[*].{InstanceId:InstanceId, HealthStatus:HealthStatus, LifecycleState:LifecycleState}" --output table
			
		Résultat attendu : Tableau avec le nombre d'instances antérieures, colonne HealthStatus en "Healthy"
		
			5: Prévenir l'administrateur en charge.