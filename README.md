# Projet Connect M1 - Mastère Expert Cloud, Sécurité et Infrastructure M1

### TABLE DES MATIÈRES

I. Récapitulatif du sujet
II. Présentation de l'infrastructure & schéma
III. Méthode de déploiement employée
IV. Déploiement de l'infrastructure
V. Test de fonctionnement
VI. Test de failover


### I. Récapitulatif du sujet

Notre équipe a sélectionné le sujet "3-Tiers classique et haute disponibilité", constistant en la conception et le déploiement via IaC d'une infrastructure résiliante hébergeant un site de E-Commerce sous Wordpress.
Plusieurs contraintes/obligations ont pu être identifiées sur ce sujet :
	- Obligation de déployer Wordpress sur des instances EC2 dans des containers Docker (la contrainte Docker a été annulée par le formateur peu de temps après le début du projet).
	- Les médias Wordpress doivent être externalisés des serveurs web sur S3.
	- La base de données doit être externalisée des serveurs web sur un service AWS dédié.
	- VPC sur-mesure avec au moins 2 zones de disponibilité.
	- Découpage en sous-réseaux strict.
	- Security Groups configurés selon le principe du moindre privilège.
	- Les instances EC2 doivent pouvoir supporter une charge irrégulière plus ou moins importante, être scalable et hautement disponible.
	- Le bucket S3 doit être sécurisé et configuré pour que les instances EC2 puissent y déposer des fichiers.
	- Une région de secours sur laquelle le site web doit pouvoir être basculée si incident sur la région principale.
	- AUCUNE INTERRUPTION DE SERVICE NE SERA TOLÉRÉE.


### II. Présentation de l'infrastructure & schéma

< insertion schéma >

Notre infrastructure hautement disponible se compose de telle sorte :
	- 1 zone publique hébergée sur Route 53 avec le nom de domaine ynov-infram1-grp1.com pour la gestion du failover du site web en cas d'incident sur la zone principale (bascule automatique).
	- 1 zone privée hébergée sur Route 53 avec le nom de domaine ynov-infram1-grp1.intra pour la gestion du failover du bucket S3 en cas d'incident sur la zone principale (bascule automatique).
	- 2 régions, us-east-1 et us-west-2, strictement identiques.
	- 2 AZ par région.
	- 1 sous-réseau publique, 2 sous-réseaux privés par AZ (un pour les instances EC2, un autre pour la base de données).
	- 1 ALB par région permettant la répartition de charge et la surveillance des instances EC2.
	- 1 ASG par région permettant le déploiement automatisé et scalable selon la charge d'instances EC2 Linux avec Docker Wordpress. 2 instances minimum, 4 instances maximum.
	- 1 NAT Gateway par région afin de fournir un accès Internet aux instances EC2 pour leur mise à disposition (configuration Docker) ainsi que 1 Internet Gateway par région.
	- 1 EFS principal répliqué sur la région secondaire sur lequel toutes les instances EC2 se connecte. Ce partage contient tous les fichiers de Wordpress.
	- 1 S3 principal répliqué sur la région secondaire sur lequel peuvent être déposés les médias envoyés sur Wordpress.
	- 1 RDS principal sous MySQL répliqué sur la région secondaire sur lequel Wordpress se connecte.

Pour la partie Sécurité, nous avons 4 Security Groups par région :
	- SG-ALB, autorisant un flux entrant depuis 0.0.0.0/0 sur les ports HTTP 80 et HTTPS 443.
	- SG-WEB, autorisant un flux entrant depuis SG-ALB sur le port HTTP 80, ainsi qu'un flux sortant vers 0.0.0.0/0 sur le port HTTPS 443 + flux sortant vers SG-DB sur le port SQL 3306 + flux sortant vers SG-EFS sur le port NFS 2049.
	- SG-EFS, autorisant un flux entrant depuis SG-WEB sur le port NFS 2049.
	- SG-DB, autorisant un flux entrant depuis SG-WEB sur le port SQL 3306


### III. Méthode de déploiement employée

