import os
from aws_cdk import Stack, CfnOutput, aws_ec2 as ec2
from constructs import Construct


class SgStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = os.getenv("VPC_PRIMARY_ID")

        # SG-ALB : HTTP/HTTPS depuis internet
        self.alb_sg = ec2.CfnSecurityGroup(self, "SgAlb",
            vpc_id=vpc_id,
            group_description="SG-ALB: HTTP/HTTPS depuis internet",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80, cidr_ip="0.0.0.0/0",
                ),
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=443, to_port=443, cidr_ip="0.0.0.0/0",
                ),
            ],
            tags=[{"key": "Name", "value": "SG-ALB-Primary"}],
        )

        # SG-Web : HTTP depuis SG-ALB uniquement
        self.web_sg = ec2.CfnSecurityGroup(self, "SgWeb",
            vpc_id=vpc_id,
            group_description="SG-Web: HTTP depuis SG-ALB uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80,
                    source_security_group_id=self.alb_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-Web-Primary"}],
        )

        # SG-DB : MySQL depuis SG-Web uniquement
        self.rds_sg = ec2.CfnSecurityGroup(self, "SgDb",
            vpc_id=vpc_id,
            group_description="SG-DB: MySQL 3306 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=3306, to_port=3306,
                    source_security_group_id=self.web_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-DB-Primary"}],
        )

        # SG-EFS : NFS 2049 depuis SG-Web uniquement
        self.efs_sg = ec2.CfnSecurityGroup(self, "SgEfs",
            vpc_id=vpc_id,
            group_description="SG-EFS: NFS 2049 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=2049, to_port=2049,
                    source_security_group_id=self.web_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-EFS-Primary"}],
        )

        # Egress NFS depuis SG-Web vers SG-EFS
        ec2.CfnSecurityGroupEgress(self, "WebToEfsEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=2049,
            to_port=2049,
            destination_security_group_id=self.efs_sg.ref,
            description="NFS sortant vers EFS",
        )

        # Egress MySQL depuis SG-Web vers SG-DB (3306)
        ec2.CfnSecurityGroupEgress(self, "WebToDbEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=3306,
            to_port=3306,
            destination_security_group_id=self.rds_sg.ref,
            description="MySQL sortant vers SG-DB",
        )

        # Egress HTTPS vers internet (pull Docker/packages/Secrets Manager au boot)
        ec2.CfnSecurityGroupEgress(self, "WebHttpsEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="0.0.0.0/0",
            description="HTTPS VERS EXT",
        )

        # Alias pour compatibilité asg_stack
        self.asg_sg = self.web_sg

        CfnOutput(self, "AlbSgId", value=self.alb_sg.ref)
        CfnOutput(self, "WebSgId", value=self.web_sg.ref)
        CfnOutput(self, "DbSgId", value=self.rds_sg.ref)
        CfnOutput(self, "EfsSgId", value=self.efs_sg.ref)


class SgStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = os.getenv("VPC_SECONDARY_ID")

        # SG-ALB
        self.alb_sg = ec2.CfnSecurityGroup(self, "SgAlb",
            vpc_id=vpc_id,
            group_description="SG-ALB: HTTP/HTTPS depuis internet",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80, cidr_ip="0.0.0.0/0",
                ),
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=443, to_port=443, cidr_ip="0.0.0.0/0",
                ),
            ],
            tags=[{"key": "Name", "value": "SG-ALB-Secondary"}],
        )

        # SG-Web
        self.web_sg = ec2.CfnSecurityGroup(self, "SgWeb",
            vpc_id=vpc_id,
            group_description="SG-Web: HTTP depuis SG-ALB uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=80, to_port=80,
                    source_security_group_id=self.alb_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-Web-Secondary"}],
        )

        # SG-DB
        self.rds_sg = ec2.CfnSecurityGroup(self, "SgDb",
            vpc_id=vpc_id,
            group_description="SG-DB: MySQL 3306 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=3306, to_port=3306,
                    source_security_group_id=self.web_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-DB-Secondary"}],
        )

        # SG-EFS
        self.efs_sg = ec2.CfnSecurityGroup(self, "SgEfs",
            vpc_id=vpc_id,
            group_description="SG-EFS: NFS 2049 depuis SG-Web uniquement",
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp", from_port=2049, to_port=2049,
                    source_security_group_id=self.web_sg.ref,
                ),
            ],
            tags=[{"key": "Name", "value": "SG-EFS-Secondary"}],
        )

        ec2.CfnSecurityGroupEgress(self, "WebToEfsEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=2049,
            to_port=2049,
            destination_security_group_id=self.efs_sg.ref,
            description="NFS sortant vers EFS",
        )

        # Egress MySQL depuis SG-Web vers SG-DB (3306)
        ec2.CfnSecurityGroupEgress(self, "WebToDbEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=3306,
            to_port=3306,
            destination_security_group_id=self.rds_sg.ref,
            description="MySQL sortant vers SG-DB",
        )

        # Egress HTTPS vers internet (pull Docker/packages/Secrets Manager au boot)
        ec2.CfnSecurityGroupEgress(self, "WebHttpsEgress",
            group_id=self.web_sg.ref,
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="0.0.0.0/0",
            description="HTTPS VERS EXT",
        )

        self.asg_sg = self.web_sg

        CfnOutput(self, "AlbSgId", value=self.alb_sg.ref)
        CfnOutput(self, "WebSgId", value=self.web_sg.ref)
        CfnOutput(self, "DbSgId", value=self.rds_sg.ref)
        CfnOutput(self, "EfsSgId", value=self.efs_sg.ref)
