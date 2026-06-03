** AWS RUNBOOK : Deployer l'infrastructure via le pipeline CI/CD GitLab (miroir GitHub) **

1. Informations generales
-------------------------
	* ID : RB-AWS-005
	* Version : 1.0
	* Auteur/Equipe : Thomas MARCILLY, equipe infra
	* Description : Permet de declencher, superviser et valider le deploiement de
	  l'infrastructure AWS (stacks CDK nested) via le pipeline CI/CD GitLab.
	  Le depot GitLab est la source de verite ; GitHub est un miroir (push mirror).

	** Point d'attention : le pipeline deploie via CDK avec CliCredentialsStackSynthesizer
	(pas de bootstrap). Toute ressource creee/modifiee doit passer par le code (infra/)
	et le pipeline, sinon elle sera ecrasee au prochain deploiement CDK. **

2. Prerequis AWS et acces
-------------------------
	* Region AWS nominale : us-east-1
	* Region AWS secours : us-west-2
	* Role/Permissions IAM : role "LabRole" (compte AWS Academy)
	* Acces GitLab : role Developer ou Maintainer sur le projet Mar-Thomasx/ynovprojetinfram1
	* Outils requis :
		- Git (client local)
		- Acces console GitLab (CI/CD > Pipelines)
		- AWS CLI (verifications)
	* Variables CI/CD GitLab requises (Settings > CI/CD > Variables), non Protected :
		- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (creds Academy, ~4h)
		- AWS_ACCOUNT_ID
		- DB_PASSWORD (mot de passe master RDS)
		- (optionnel) WP_ADMIN_PASSWORD, WP_DB_PASSWORD, WP_ADMIN_EMAIL

3. Environnement & ressources cibles
------------------------------------
	* Depot source : GitLab (gitlab.com/Mar-Thomasx/ynovprojetinfram1)
	* Miroir : GitHub (push mirror automatique depuis GitLab)
	* Fichier pipeline : .gitlab-ci.yml
	* Buckets d'assets CDK (templates nested) :
		- ynov-cdk-assets-<ACCOUNT_ID>-use1 (us-east-1)
		- ynov-cdk-assets-<ACCOUNT_ID>-usw2 (us-west-2)
	* Stages du pipeline (ordre) :
		- secrets           : cree les secrets Secrets Manager (2 regions)
		- deploy-secondary  : deploie InfraSecondaryStack (us-west-2)
		- deploy-primary    : deploie InfraPrimaryStack (us-east-1) + Route53 failover
		- dr                : snapshot RDS cross-region (manuel/planifie)
	* Stacks CloudFormation cibles :
		- InfraPrimaryStack (us-east-1) + nested (VPC, SG, RDS, EFS, ALB, ASG, S3, Route53)
		- InfraSecondaryStack (us-west-2) + nested

4. Procedure etape par etape
----------------------------
	1- Verification de l'etat initial
		* Option A : console GitLab
			1: Aller sur le projet > Build > Pipelines
			2: Verifier que le dernier pipeline de la branche est en statut "passed" (vert)

		Resultat attendu : dernier pipeline "passed"

		* Option B : AWS CLI
			1: Verifier les stacks : aws cloudformation list-stacks --region us-east-1 --query "StackSummaries[?StackStatus=='CREATE_COMPLETE'||StackStatus=='UPDATE_COMPLETE'].StackName" --output table
			2: Idem region us-west-2

		Resultat attendu : InfraPrimaryStack / InfraSecondaryStack en COMPLETE

	2- Mettre a jour les credentials AWS Academy (si expires, ~4h)
		1: Sur AWS Academy > Learner Lab > AWS Details, copier les nouveaux credentials
		2: GitLab > Settings > CI/CD > Variables : mettre a jour AWS_ACCESS_KEY_ID,
		   AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_ACCOUNT_ID

		Resultat attendu : variables a jour (sinon les jobs echouent avec erreur d'authentification)

	3- Modifier le code et declencher le deploiement
		1: Recuperer la derniere version : git pull gitlab main
		2: Se placer sur sa branche de travail : git checkout <ma-branche>
		3: Integrer main si besoin : git merge main
		4: Modifier les fichiers dans infra/ (stacks, user_data, etc.)
		5: Commiter : git add infra/ && git commit -m "<message>"
		6: Pousser : git push gitlab <ma-branche>

		Resultat attendu : un nouveau pipeline se declenche automatiquement
		(declenchement sur changement de infra/**)

	4- Superviser le pipeline
		1: GitLab > Build > Pipelines > ouvrir le pipeline en cours
		2: Suivre l'enchainement des stages : secrets > deploy-secondary > deploy-primary
		3: En cas d'echec d'un job, ouvrir le job pour lire les logs

		Resultat attendu : les 3 stages passent au vert dans l'ordre

	5- Validation du deploiement
		1: AWS CLI : aws cloudformation describe-stacks --stack-name InfraPrimaryStack --region us-east-1 --query "Stacks[0].StackStatus" --output text
		2: Tester le site via le DNS de l'ALB (ou le FQDN Route53 sub.ynov-infram1-grp1.com)

		Resultat attendu : StackStatus UPDATE_COMPLETE / CREATE_COMPLETE et site accessible

	6- Snapshot DR RDS (operation planifiee ou manuelle)
		* Manuel : GitLab > Pipelines > pipeline en cours > lancer le job "rds-snapshot-dr" (play)
		* Planifie : GitLab > Build > Pipeline schedules > New schedule, cron "0 * * * *"

		Resultat attendu : snapshot wordpress-primary-snap-<date> cree en us-east-1 et copie en us-west-2

5. Procedure de rollback en cas d'echec
---------------------------------------
	** Principe : revenir au dernier commit fonctionnel et laisser le pipeline redeployer. **

	* Option A : revert via Git (recommande)
		1: Identifier le commit fautif : git log --oneline -5
		2: Annuler le dernier commit : git revert <hash_commit_fautif>
		3: Pousser : git push gitlab <ma-branche>

		Resultat attendu : un pipeline se declenche et redeploie la version precedente (CDK idempotent)

	* Option B : revert via la console GitLab
		1: Ouvrir le commit fautif (Code > Commits)
		2: Cliquer sur "Revert", choisir la branche cible
		3: Le pipeline se relance automatiquement

	* Option C : stack CloudFormation bloque (ROLLBACK_COMPLETE / REVIEW_IN_PROGRESS)
		1: Supprimer le stack bloque :
		   aws cloudformation delete-stack --stack-name <Stack> --region <Region>
		2: Attendre : aws cloudformation wait stack-delete-complete --stack-name <Stack> --region <Region>
		3: Relancer le pipeline (le stack sera recree proprement)

		Resultat attendu : stack recree en CREATE_COMPLETE au prochain pipeline

	** Dans tous les cas : prevenir l'administrateur en charge et noter l'incident dans le journal de bord. **
