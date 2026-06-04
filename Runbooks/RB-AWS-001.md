** AWS RUNBOOK : Ajout d'un Listener HTTPS (Port 443) sur l'ALB **

1. Informations générales
-------------------------
	* ID : RB-AWS-001
	* Version : 1.0
	* Auteur/Équipe : Paul Hamon, Groupe Tiers classique et haute disponibilité
	* Description : Ce runbook permet d'ajouter manuellement un Listener sur le port 443 (HTTPS) à l'Application Load Balancer principal et d'y attacher un certificat SSL/TLS pour sécuriser le trafic web.
	
2. Prérequis AWS et accès
-------------------------
	* Région AWS nominale : us-east-1 (N. Virginia)
	* Rôle/Permissions IAM : Droits d'accès en modification sur ELBv2 (Elastic Load Balancing) et accès en lecture sur ACM (AWS Certificate Manager)
	* Outils requis :
		- Disposer de l'ARN d'un certificat SSL/TLS valide créé dans AWS Certificate Manager
		- Console web AWS (Accès Navigateur)
		- AWS CLI (configuré)

3. Environnement & ressources cibles
------------------------------------
	* Nom du Stack CloudFormation : AlbStackPrimary
	* Nom des ressources concernées :
		- Application Load Balancer AlbPrimary
		- Target Group TargetGroupPrimary
		
4. Procédure étape par étape
----------------------------
	1- Vérification de l'état initial (pré-check)
		* Option B : AWS CLI
			1: Avant de commencer, assurez-vous que l'ALB est actif et récupérez son ARN.
			2: Exécutez la commande : aws elbv2 describe-load-balancers --names AlbPrimary --region us-east-1
		
		Résultat attendu : Le statut ("State") doit afficher "active".
		
	2- Exécution de l'action principale : Ajout du Listener HTTPS sur le port 443
		* Option A : Console web AWS
			1: Allez sur le service EC2 > Load Balancers.
			2: Sélectionnez l'instance AlbPrimary.
			3: Allez dans l'onglet "Listeners", puis cliquez sur "Add listener".
			4: Sélectionnez le protocole HTTPS, port 443. Redirigez vers le TargetGroupPrimary et sélectionnez le certificat SSL ACM.
			
		* Option B : AWS CLI
			1: Exécuter la commande : aws elbv2 create-listener --load-balancer-arn [ARN_DE_L_ALB] --protocol HTTPS --port 443 --certificates CertificateArn=[ARN_DU_CERTIFICAT_ACM] --default-actions Type=forward,TargetGroupArn=[ARN_DU_TARGET_GROUP] --region us-east-1
	
	3- Application du changement
		* Option B : AWS CLI
			1: Pour forcer l'utilisation du HTTPS, modifiez le Listener HTTP (Port 80) existant pour qu'il redirige automatiquement le trafic vers le port 443.
			2: Exécuter la commande : aws elbv2 modify-listener --listener-arn [ARN_DU_LISTENER_80] --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"

	4- Validation (Post-check)
		* Option B : Terminal
			1: Validez que l'application répond correctement en HTTPS avec le certificat en exécutant : curl -I https://[DNS_DE_L_ALB]
			
		Résultat attendu : Le terminal doit renvoyer un code HTTP 200 OK (si testé directement sur le 443) ou un HTTP 301 Moved Permanently (si testé sur le port 80 vers le 443).

5. Procédure de rollback en cas d'échec
---------------------------------------		
		* Si l'étape 4 échoue (erreur de certificat ou inaccessibilité), annulez immédiatement les modifications :
			1: Supprimez le Listener HTTPS avec la commande : aws elbv2 delete-listener --listener-arn [ARN_DU_LISTENER_443]
			2: Remettez la configuration d'origine du port 80 en mode "forward" vers le Target Group.
			
		NB : Pour l'exercice académique de rédaction de Runbook, le cas d'usage est pertinent mais en environnement de production réel, ce Runbook ne devrait pas lister des commandes CLI, il devrait expliquer comment modifier le script alb_stack.py et pousser sur GitLab pour que la pipeline exécute les actions.