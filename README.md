# Launch Configuration to Launch Templates Conversion Tool

This tool attempts to port EC2 Auto Scaling Launch Configurations into EC2 Launch Templates for all regions in a single AWS account.

## Running the tool
This tool was designed to run into an [AWS CloudShell](https://aws.amazon.com/cloudshell/) environment or through [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html).

### Required Permissions
The tool uses the caller's permissions (or [IAM role](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) if ran from an EC2 Instance) to perform its function. Be sure that the caller/role is allowed to perform the following actions:

- `autoscaling:DescribeLaunchConfigurations`
- `autoscaling:DescribeAutoScalingGroups`
- `ec2:DescribeRegions`
- `ec2:CreateLaunchTemplate`


### AWS CloudShell / CLI
1. Copy lc2lt.py to your local environment.
```
curl -O "https://raw.githubusercontent.com/aws-samples/ec2autoscaling-launchconfiguration-to-launchtemplate/main/lc2lt.py"
```
2. Execute the script:
```
python3 lc2lt.py
```

### Customization Variables
The behavior of the tool can be changed by changing the variables under "Defaults" on the top of the tool.

- `autoscaling_describe_page_size` (Default `100``): The size of the result pages to Describe API calls made to the EC2 Auto Scaling Endpoint. Generally should not be adjusted unless time-out errors are occurring. More information can be found on the [AWS CLI Documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-pagination.html)
- `logfile` (Default `lc2lt_results.csv`): The name of the log which will contain the list of launch configurations and the outcome of the conversion, in CSV format.
- `retain_spot_price` (Default `True`): In order to use Spot Instances, Launch Configurations required a max spot price to be defined. This is no longer the case with Launch Templates. If set to `False` the value will not be carried over to the Launch Template, which will [cap it](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-leveraging-ec2-spot-instances/how-spot-instances-work.html) at the On-Demand price. Currently as the prices [no longer value](https://aws.amazon.com/blogs/compute/new-amazon-ec2-spot-pricing/) widely, it is considered a best practice to leave it unset (`False`). 
- `dry_run` (Default: `False`): If set to `True`, no changes are made. Used only to test permissions.

```
# Defaults
autoscaling_describe_page_size = 100
retain_spot_price = True
logfile = "lc2lt_results.csv"
dry_run = False
```

## Security
See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.
## License

This library is licensed under the MIT-0 License. See the LICENSE file.