import aws_cdk as cdk
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_s3 as s3
from constructs import Construct


class Stack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        region: str,
        account: str,
        image_repository: str,
        calendars_bucket_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        calendars_bucket = s3.Bucket.from_bucket_name(
            self,
            'CalendarsBucket',
            bucket_name=calendars_bucket_name,
        )

        image = ecs.EcrImage.from_registry(image_repository)

        vpc = ec2.Vpc.from_lookup(
            self,
            'Vpc',
            region=region,
            is_default=True,
            owner_account_id=account,
        )

        cluster = ecs.Cluster(
            self,
            'Cluster',
            vpc=vpc,
        )
        cluster.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        scheduled_fargate_task = ecs_patterns.ScheduledFargateTask(
            self,
            'Schedule',
            cluster=cluster,
            scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                image=image,
                memory_limit_mib=2048,
                environment={
                    'CALENDARS_BUCKET_NAME': calendars_bucket.bucket_name,
                },
            ),
            schedule=appscaling.Schedule.cron(hour='10', minute='0', day='1'),
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        calendars_bucket.grant_write(scheduled_fargate_task.task_definition.task_role)
