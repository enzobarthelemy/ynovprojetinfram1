import os
from aws_cdk import Stack, CfnOutput, CfnParameter, aws_rds as rds
from constructs import Construct


class RdsStackPrimary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_subnet_1 = CfnParameter(self, "DbSubnet1Id", type="String").value_as_string
        db_subnet_2 = CfnParameter(self, "DbSubnet2Id", type="String").value_as_string
        db_sg_id    = CfnParameter(self, "DbSgId", type="String").value_as_string
        db_password = CfnParameter(self, "DbPassword", type="String", no_echo=True).value_as_string

        # Subnet group couvrant les 2 AZ (us-east-1a + us-east-1b)
        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroupPrimary",
            db_subnet_group_description="Subnet group RDS WordPress Primary",
            subnet_ids=[db_subnet_1, db_subnet_2],
            tags=[{"key": "Name", "value": "rds-subnet-group-primary"}],
        )

        # Instance RDS MySQL — Enhanced Monitoring désactivé (Student)
        db = rds.CfnDBInstance(self, "RdsPrimary",
            db_instance_identifier="wordpress-rds-primary",
            db_instance_class="db.t3.micro",
            engine="mysql",
            engine_version="8.0",
            allocated_storage="20",
            storage_type="gp2",
            master_username="admin",
            master_user_password=db_password,
            db_subnet_group_name=subnet_group.ref,
            vpc_security_groups=[db_sg_id],
            multi_az=False,
            publicly_accessible=False,
            monitoring_interval=0,
            deletion_protection=False,
            backup_retention_period=7,
            tags=[{"key": "Name", "value": "wordpress-rds-primary"}],
        )

        CfnOutput(self, "RdsEndpoint", value=db.attr_endpoint_address)
        CfnOutput(self, "RdsPort", value=db.attr_endpoint_port)


class RdsStackSecondary(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_subnet_1 = CfnParameter(self, "DbSubnet1Id", type="String").value_as_string
        db_subnet_2 = CfnParameter(self, "DbSubnet2Id", type="String").value_as_string
        db_sg_id    = CfnParameter(self, "DbSgId", type="String").value_as_string
        db_password = CfnParameter(self, "DbPassword", type="String", no_echo=True).value_as_string

        # Subnet group couvrant les 2 AZ (us-west-2a + us-west-2b)
        subnet_group = rds.CfnDBSubnetGroup(self, "RdsSubnetGroupSecondary",
            db_subnet_group_description="Subnet group RDS WordPress Secondary",
            subnet_ids=[db_subnet_1, db_subnet_2],
            tags=[{"key": "Name", "value": "rds-subnet-group-secondary"}],
        )

        # Instance RDS MySQL — Enhanced Monitoring désactivé (Student)
        db = rds.CfnDBInstance(self, "RdsSecondary",
            db_instance_identifier="wordpress-rds-secondary",
            db_instance_class="db.t3.micro",
            engine="mysql",
            engine_version="8.0",
            allocated_storage="20",
            storage_type="gp2",
            master_username="admin",
            master_user_password=db_password,
            db_subnet_group_name=subnet_group.ref,
            vpc_security_groups=[db_sg_id],
            multi_az=False,
            publicly_accessible=False,
            monitoring_interval=0,
            deletion_protection=False,
            backup_retention_period=7,
            tags=[{"key": "Name", "value": "wordpress-rds-secondary"}],
        )

        CfnOutput(self, "RdsEndpoint", value=db.attr_endpoint_address)
        CfnOutput(self, "RdsPort", value=db.attr_endpoint_port)
