# Table des matières
I- Informations générales
II- Prérequis AWS & accès
III- Environnement & ressources cibles
IV- Procédure étape par étape
A. Étape 1 : Vérification de l'état initial (pré-check)
B. Étape 2 : Exécution de l'action principale Ajout du Listener HTTPS sur le port 443.
a) Option A (Via la Console AWS)
b) Option B (Via AWS CLI) :
C. Étape 3 : Application du changement
D. Étape 4 : Validation (Post-check)
V- Procédure de rollback (en cas d'échec)

## I- Informations générales
ID du Runbook: RB-AWS-001
Version : 1.0 
Auteur / Équipe: Paul Hamon / Groupe Tiers classique et haute disponibilité 
Description: Ce runbook permet d'ajouter manuellement un Listener sur le port 443 (HTTPS) à l'Application Load Balancer principal et d'y attacher un certificat SSL/TLS pour sécuriser le trafic web.

## II- Prérequis AWS & accès
Pour exécuter ce runbook, vous devez disposer des éléments suivants :
Région AWS: us-east-1 (N. Virginia)
Rôle / Permissions IAM: Droits d'accès en modification sur ELBv2 (Elastic Load Balancing) et accès en lecture sur ACM (AWS Certificate Manager).
Disposer de l'ARN d'un certificat SSL/TLS valide créé dans AWS Certificate Manager
Outils requis: AWS CLI (configuré) ou Console AWS (Accès Navigateur)

## III- Environnement & ressources cibles
Identifiez précisément les ressources sur lesquelles vous allez agir :
Nom du Stack CloudFormation : AlbStackPrimary
ID/Nom de la ressource principale : Application Load Balancer AlbPrimary et son Target Group TargetGroupPrimary

## IV- Procédure étape par étape

### A. Étape 1 : Vérification de l'état initial (pré-check)
Avant de commencer, assurez-vous que l'ALB est actif et récupérez son ARN.
Exécutez la commande suivante :
`aws elbv2 describe-load-balancers --names AlbPrimary --region us-east-1`
Attendu : Le statut ("State") doit afficher "active".

### B. Étape 2 : Exécution de l'action principale Ajout du Listener HTTPS sur le port 443.

**a) Option A (Via la Console AWS)**
1. Allez sur le service EC2 > Load Balancers.
2. Sélectionnez l'instance AlbPrimary.
3. Allez dans l'onglet "Listeners", puis cliquez sur "Add listener".
4. Sélectionnez le protocole HTTPS, port 443. Redirigez vers le TargetGroupPrimary et sélectionnez le certificat SSL ACM.

**b) Option B (Via AWS CLI) :**
`aws elbv2 create-listener --load-balancer-arn [ARN_DE_L_ALB] --protocol HTTPS --port 443 --certificates CertificateArn=[ARN_DU_CERTIFICAT_ACM] --default-actions Type=forward,TargetGroupArn=[ARN_DU_TARGET_GROUP] --region us-east-1`

### C. Étape 3 : Application du changement
Pour forcer l'utilisation du HTTPS, modifiez le Listener HTTP (Port 80) existant pour qu'il redirige automatiquement le trafic vers le port 443.
`aws elbv2 modify-listener --listener-arn [ARN_DU_LISTENER_80] --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"`

### D. Étape 4 : Validation (Post-check)
Validez que l'application répond correctement en HTTPS avec le certificat : 
`curl -I https://[DNS_DE_L_ALB]` 
Attendu: Le terminal doit renvoyer un code HTTP 200 OK (si testé directement sur le 443) ou un HTTP 301 Moved Permanently (si testé sur le port 80 vers le 443).

## V- Procédure de rollback (en cas d'échec)
Si l'étape 4 échoue (erreur de certificat ou inaccessibilité), annulez immédiatement les modifications :
Supprimez le Listener HTTPS : 
`aws elbv2 delete-listener --listener-arn [ARN_DU_LISTENER_443]`
Remettez la configuration d'origine du port 80 en mode "forward" vers le Target Group.

NB : Pour l'exercice académique de rédaction de Runbook, le cas d'usage est pertinent mais en environnement de production réel, ce Runbook ne devrait pas lister des commandes CLI, il devrait expliquer comment modifier le script alb_stack.py et pousser sur GitLab pour que la pipeline exécute les actions.