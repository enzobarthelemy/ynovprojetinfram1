* Titre : ADR 007 - Chaîne CI/CD GitLab + miroir GitHub

* Contexte : L'infrastructure (CDK Python) doit être déployée de façon automatisée, reproductible et traçable, sans intervention manuelle sur la console AWS. Le compte AWS Academy interdit le bootstrap CDK et l'environnement impose des identifiants temporaires. Il faut aussi respecter la contrainte de collaboration (GitHub) tout en disposant d'un moteur CI/CD complet.

* Décision : Utilisation de **GitLab CI/CD** comme moteur de déploiement (pipeline `.gitlab-ci.yml` multi-stages) car il offre des fonctionnalités natives indispensables ici : stages ordonnés, déclenchement manuel (`when: manual`), planification (schedules), `resource_group` pour sérialiser les déploiements et règles conditionnelles (`rules`/`changes`). GitHub est conservé en **miroir push** (mirroring) pour la collaboration et la visibilité, GitLab restant la source de vérité du déploiement.

* Conséquences :
	- Pipeline GitLab orchestrant le déploiement bout-en-bout :
		- `secrets` : création/MAJ des secrets (Secrets Manager) dans les 2 régions
		- `deploy-secondary` → `deploy-primary` → `seed-west-db` → `deploy-secondary-compute` : déploiement ordonné des nested stacks (gestion de la dépendance cross-région). `seed-west-db` restaure une base en us-west-2 depuis un snapshot de la primaire pour rendre les 2 régions actives (active-active)
		- `dr` : snapshot RDS cross-région (planifié horaire / manuel)
		- `failover` / `failback` : bascule et retour, déclenchés via l'input GitLab `run_mode` (valeurs `failover` / `failback`)
	- Authentification AWS via identifiants du runner CI (`CliCredentialsStackSynthesizer`), sans bootstrap CDK
	- Variables sensibles (mots de passe, IDs) stockées en variables CI/CD GitLab, jamais en clair dans le dépôt
	- Configuration d'un **miroir push GitLab → GitHub** (Settings → Repository → Mirroring) pour synchroniser le code vers GitHub
	- Règle `if schedule → when: never` sur les jobs de déploiement pour qu'un run planifié ne redéploie pas l'infra (seul le job de snapshot DR s'exécute)
