from aws_cdk import NestedStack, aws_ec2 as ec2
from constructs import Construct


class SgNested(NestedStack):
    """
    Security Groups en NestedStack. Recoit le vpc_id directement (pas de CfnParameter).
    Expose alb_sg, web_sg, rds_sg, efs_sg (+ alias asg_sg).
    name : "Primary" ou "Secondary" (pour les tags)
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 vpc_id: str, name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SG-ALB : HTTP/HTTPS depuis internet
        self.alb_sg = ec2.CfnSecurityGroup(self, "SgAlb",
            vpc_id=vpc_id,
            group_description="SG-ALB: HTTP/HTTPS depuis internet",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80, cidr_ip="0.0.0.0/0"),
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=443, to_port=443, cidr_ip="0.0.0.0/0"),
            ],
            tags=[{"key": "Name", "value": f"SG-ALB-{name}"}],
        )

        # SG-Web : HTTP depuis SG-ALB uniquement
        self.web_sg = ec2.CfnSecurityGroup(self, "SgWeb",
            vpc_id=vpc_id,
            group_description="SG-Web: HTTP depuis SG-ALB uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80,
                    source_security_group_id=self.alb_sg.ref),
            ],
            tags=[{"key": "Name", "value": f"SG-Web-{name}"}],
        )

        # SG-DB : MySQL 3306 depuis SG-Web uniquement
        self.rds_sg = ec2.CfnSecurityGroup(self, "SgDb",
            vpc_id=vpc_id,
            group_description="SG-DB: MySQL 3306 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=3306, to_port=3306,
                    source_security_group_id=self.web_sg.ref),
            ],
            tags=[{"key": "Name", "value": f"SG-DB-{name}"}],
        )

        # SG-EFS : NFS 2049 depuis SG-Web uniquement
        self.efs_sg = ec2.CfnSecurityGroup(self, "SgEfs",
            vpc_id=vpc_id,
            group_description="SG-EFS: NFS 2049 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=2049, to_port=2049,
                    source_security_group_id=self.web_sg.ref),
            ],
            tags=[{"key": "Name", "value": f"SG-EFS-{name}"}],
        )

        # Egress SG-Web : NFS vers EFS
        ec2.CfnSecurityGroupEgress(self, "WebToEfsEgress",
            group_id=self.web_sg.ref, ip_protocol="tcp",
            from_port=2049, to_port=2049,
            destination_security_group_id=self.efs_sg.ref,
            description="NFS sortant vers EFS")

        # Egress SG-Web : MySQL vers DB
        ec2.CfnSecurityGroupEgress(self, "WebToDbEgress",
            group_id=self.web_sg.ref, ip_protocol="tcp",
            from_port=3306, to_port=3306,
            destination_security_group_id=self.rds_sg.ref,
            description="MySQL sortant vers SG-DB")

        # Egress SG-Web : HTTPS vers internet (boot : Docker/packages/Secrets)
        ec2.CfnSecurityGroupEgress(self, "WebHttpsEgress",
            group_id=self.web_sg.ref, ip_protocol="tcp",
            from_port=443, to_port=443, cidr_ip="0.0.0.0/0",
            description="HTTPS VERS EXT")

        # Alias pour l'ASG
        self.asg_sg = self.web_sg
