import boto3
import csv
import logging
import sys


from botocore.exceptions import ClientError

# Defaults
autoscaling_describe_page_size = 100
retain_spot_price = True
logfile = "lc2lt_results.csv"
dry_run = False

# Logger Settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def write_logfile(file, results):
    """ Writes the outcome of the conversion to a CSV logfile
    """
    logger.info('Saving conversion results to file: {}'.format(file))

    try:
        data_file = open(file, 'w', newline='')
        csv_writer = csv.writer(data_file)
        
        count = 0
        for data in results:
            if count == 0:
                header = data.keys()
                csv_writer.writerow(header)
                count += 1
            csv_writer.writerow(data.values())
    finally:
        data_file.close()

    return

def paginate(method, **kwargs):
    """ Paginates Responses from API Calls.
    """
    client = method.__self__

    try:
        paginator = client.get_paginator(method.__name__)
        for page in paginator.paginate(**kwargs).result_key_iters():
            for item in page:
                yield item

    except ClientError as e:
        error_message = 'Error paginating API Response: {}'.format(error)
        logger.error(error_message)
        raise Exception(error_message)

def get_credentials():
    """ Gets the AWS credentials for the default identity
    """
    try:
        sts_client = boto3.client('sts')
        credentials = sts_client.get_caller_identity()

        message = "Using credential {arn} for {account}".format(arn=credentials['Arn'],account=credentials['Account'])
        logger.info(message)
        return credentials

    except ClientError as error:
        error_message = 'Error getting STS credentials: {}'.format(error)
        print(error_message)

def get_regions(account_id):
    """ Returns the regions enabled for the AWS Account
    """
    regions = []
    try:
        ec2_client = boto3.client('ec2')

        response = ec2_client.describe_regions(AllRegions=False)

        for region in response['Regions']:
            regions.append(region['RegionName'])

    except ClientError as error:
        error_message = 'Error getting list of regions: {}'.format(error)
        print(error_message)
    
    message = "Enabled regions: {}".format(regions)
    logger.info(message)
    return regions 

def get_launch_configurations(**kwargs):
    """ Returns the lunch configurations on a given region
    """
    try:
        autoscaling_client = boto3.client('autoscaling',**kwargs)
        paginated_response = paginate(autoscaling_client.describe_launch_configurations,PaginationConfig={'PageSize': autoscaling_describe_page_size})

        launch_configurations = []
        for launch_configuration in paginated_response:
            launch_configurations.append(launch_configuration)

        message = "Launch Configurations Found: {}".format(len(launch_configurations))
        logger.info(message)
        return launch_configurations

    except ClientError as error:
        error_message = 'Error getting Launch Configurations: {}'.format(error)
        print(error_message)
        
def prepare_launch_template_data(launch_configuration, retain_spot_price):
    """ Returns the converted launch configuration
    """

    launch_template_data={}

    # Mandatory parameters
    launch_template_data['ImageId']=launch_configuration['ImageId']
    launch_template_data['InstanceType']=launch_configuration['InstanceType']

    launch_template_data['EbsOptimized']=launch_configuration['EbsOptimized']

    # Optional parameters.
    if launch_configuration['KeyName']:
        launch_template_data['KeyName']=launch_configuration['KeyName']
    
    if launch_configuration['KernelId']:
        launch_template_data['KernelId']=launch_configuration['KernelId']

    if launch_configuration['UserData']:
        launch_template_data['UserData']=launch_configuration['UserData']

    # Special handling
    if launch_configuration['RamdiskId']:
        launch_template_data['RamDiskId']=launch_configuration['RamdiskId']

    if 'BlockDeviceMappings' in launch_configuration:
        for bdm in launch_configuration['BlockDeviceMappings']:
            if 'NoDevice' in bdm:
                bdm['NoDevice'] = ""
        launch_template_data['BlockDeviceMappings']=launch_configuration['BlockDeviceMappings']

    if 'MetadataOptions' in launch_configuration:
        launch_template_data['MetadataOptions']=launch_configuration['MetadataOptions']

    if 'PlacementTenancy' in launch_configuration:
        launch_template_data['Placement']={'Tenancy':launch_configuration['PlacementTenancy']}

    if launch_configuration['SecurityGroups']:
        if 'AssociatePublicIpAddress' in launch_configuration:
            launch_template_data['NetworkInterfaces']=[{'AssociatePublicIpAddress':True,
                                                        'Groups':launch_configuration['SecurityGroups'],
                                                        'DeviceIndex':0}]
        else:
            launch_template_data['SecurityGroupIds']=launch_configuration['SecurityGroups']
    else:
        if 'AssociatePublicIpAddress' in launch_configuration:
            launch_template_data['NetworkInterfaces']=[{'AssociatePublicIpAddress':True,
                                                        'DeviceIndex':0}]

    if 'SpotPrice' in launch_configuration:
        launch_template_data['InstanceMarketOptions']={'MarketType':'spot'}
        if retain_spot_price:
            launch_template_data['InstanceMarketOptions']['SpotOptions']={'MaxPrice':launch_configuration['SpotPrice']}        

    if 'InstanceMonitoring' in launch_configuration:
        launch_template_data['Monitoring']={'Enabled':True}

    if 'IamInstanceProfile' in launch_configuration:
        if launch_configuration['IamInstanceProfile'].startswith('arn:'):
            launch_template_data['IamInstanceProfile']={'Arn':launch_configuration['IamInstanceProfile']}
        else:
            launch_template_data['IamInstanceProfile']={'Name':launch_configuration['IamInstanceProfile']}

    return launch_template_data

def create_launch_template(launch_configuration,**kwargs):
    """Creates the Launch Template
    """
    launch_config_name=launch_configuration['LaunchConfigurationName']
    launch_template_name='N/A'
    launch_template_id='N/A'
    notes=''

    if (len(launch_configuration['LaunchConfigurationName'])<3):
        launch_template_name=launch_configuration['LaunchConfigurationName']+'_LC'
        notes='Launch Configuration name with less than 3 characters. Appended \'_LC\' to the name.'
    else:
        launch_template_name=launch_configuration['LaunchConfigurationName']

    try:
        ec2_client = boto3.client('ec2',**kwargs)
        response= ec2_client.create_launch_template(
            LaunchTemplateName=launch_template_name,
            VersionDescription='Converted from EC2 Auto Scaling Launch Configuration '+launch_configuration['LaunchConfigurationARN'],
            LaunchTemplateData={
            **prepare_launch_template_data(launch_configuration,retain_spot_price)
            },
            DryRun=dry_run)

        launch_template_id=response['LaunchTemplate']['LaunchTemplateId']
        launch_template_creator=response['LaunchTemplate']['CreatedBy']
        launch_template_creation_time=response['LaunchTemplate']['CreateTime']
        message = "Converted {}".format(launch_config_name)

        logger.info(message) 
   

    except ClientError as error:
        if error.response['Error']['Code'] == 'DryRunOperation':
            notes='DryRun operation.'
            error_message="Failed to convert {}: {}".format(launch_config_name,notes)

        elif error.response['Error']['Code'] == 'InvalidLaunchTemplateName.AlreadyExistsException':
            notes='A Launch Template with the same name already exists.'
            error_message="Failed to convert {}: {}".format(launch_config_name,notes)
        else:
            notes=error
            error_message="Failed to convert {}: {}".format(launch_config_name,notes)
        logger.error(error_message)

    return {
            'lconfig_name'           : launch_config_name,
            'ltemplate_name'           : launch_template_name,
            'ltemplate_id'             : launch_template_id,
            'conversion_notes'  : notes
        }

def main():
    credentials=get_credentials()
    account_id=credentials['Account']
    regions=get_regions(account_id)
    log=[]

    for region in regions:
        logger.info('Getting Launch Configurations for: {}'.format(region))
        launch_configurations=(get_launch_configurations(region_name=region))

        for launch_config in launch_configurations:
            result = create_launch_template(launch_config,region_name=region)
            log.append({
                'account_id'    : account_id,
                'region'        : region,
                **result
            })

    write_logfile(logfile,log)

if __name__ == "__main__":
    main()