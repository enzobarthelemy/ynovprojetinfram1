* Titre : ADR 005 - Configuration EFS

* Contexte : L'infrastructure se doit d'être résiliente et évolutive selon les contraintes demandées : "aucune interruption de service ne sera tolérée"

* Décision : Mise en place d'un partage de fichier EFS pour les fichiers de configuration EFS + réplication inter-région

* Conséquences :
	- Configuration d'un EFS principal sur us-east-1 + réplication sur us-west-2
	- Montage automatique du partage EFS sur les instances EC2 via le script user_data.sh
	- Wordpress s'installe dans ce partage de fichier et est synchronisé entre toutes les instances EC2