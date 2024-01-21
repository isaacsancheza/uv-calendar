import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_ecs_patterns as ecs_patterns
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
            **kwargs
        ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(
            self, 
            'Bucket', 
            removal_policy=cdk.RemovalPolicy.DESTROY, 
            auto_delete_objects=True,
          )
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
                    'BUCKET_NAME': bucket.bucket_name,
                    'CALENDARS_BUCKET_NAME': calendars_bucket.bucket_name,
                },
            ),
            schedule=appscaling.Schedule.rate(cdk.Duration.days(7)),
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        
        bucket.grant_read_write(scheduled_fargate_task.task_definition.task_role)
        calendars_bucket.grant_write(scheduled_fargate_task.task_definition.task_role)
        
        cdk.CfnOutput(
            self,
            'BucketName',
            value=bucket.bucket_name,
        )
        cdk.CfnOutput(
            self,
            'CalendarsBucketName',
            value=calendars_bucket.bucket_name,
        )
