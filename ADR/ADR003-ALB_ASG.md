* Titre : ADR 003 - Configuration ALB/ASG

* Contexte : L'infrastructure se doit d'être résiliente et évolutive selon les contraintes demandées : "aucune interruption de service ne sera tolérée"

* Décision : Mise en place d'un ALB pour la répartition de charges + Mise en place d'un ASG pour l'adaptation des serveurs Web face à l'irrégularité du trafic

* Conséquences :
	- Configuration d'un ASG entre 2 AZ du VPC :
		- Minimum 2 VMs
		- Maximum 4 VMs
	- Configuration d'un ALB entre les 2 AZ du VPC :
		- Écoute du port web (80)
		- Activation du Stickness pour éviter le changement de serveur pendant la navigation sur le site (nécessite cookies)