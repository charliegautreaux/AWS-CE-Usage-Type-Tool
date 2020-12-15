import json
import boto3
from datetime import datetime, timedelta
import os


def handler(event, context):
    '''set variables'''
    customer = os.environ['customer_name']
    bucket = os.environ['s3_bucket']
    today = datetime.utcnow()
    timestamp = today.strftime("%Y-%m-%d_%H:%M")

    '''configure reports to run'''
    reports = {'RDS': ['RDS: Storage', ],
               'DynamoDB': ['DDB: Indexed Data Storage', ],
               'S3': ['S3: Storage - Standard', ],
               'EBS-Snaps': ['EC2: EBS - Snapshots', ],
               'EBS-Vols': ['EC2: EBS - HDD(sc1)',
                            'EC2: EBS - HDD(st1)',
                            'EC2: EBS - Magnetic',
                            'EC2: EBS - Provisioned IOPS',
                            'EC2: EBS - Provisioned IOPS(io2)',
                            'EC2: EBS - SSD(gp2)',
                            'EC2: EBS - SSD(io1)', 'EC2: EBS - SSD(io2)']
               }

    '''retreive list of regions from AWS'''
    regionlist = get_regions()
    print(f'Reporting on the following AWS Regions: {regionlist}')

    '''run reports'''
    for key, value in reports.items():
        try:
            records = []
            print(f'reporting on {key}')
            records = ce_report(value, key, regionlist)
            convertJSON_S3(bucket,
                           f'{customer}-{timestamp}-{key}.json',
                           records)

        except Exception as e:
            print(f'report exception {e}')

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }


def get_regions():
    '''get list of aws regions'''
    regionlist = []
    ec2 = boto3.client('ec2')
    response = ec2.describe_regions()['Regions']
    for _ in range(len(response)):
        region = response[_]['RegionName']
        regionlist.append(region)
    return regionlist


def ce_report(usage_type, record_type, regionlist):
    '''getting dates (yyyy-MM-dd) and converting to string'''
    now = datetime.utcnow()
    neg12months = now - timedelta(days=365)
    end = now.strftime("%Y-%m-01")
    start = neg12months.strftime("%Y-%m-01")
    print(f'Getting cost and usage from {start} to {end}')
    records = []

    # connecting to cost explorer to get monthly aws usage
    ce = boto3.client('ce')
    for region in regionlist:
        print(f'Getting cost and usage from {region} for {record_type}')
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start,
                'End': end
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost', 'UsageQuantity'],
            Filter={
                "And": [{
                    "Dimensions": {
                        "Key": "USAGE_TYPE_GROUP",
                        "Values": usage_type
                    }
                },
                 {"Dimensions": {
                        "Key": "REGION",
                        "Values": [region, ]
                        }
                  }
                ]},
            GroupBy=[
                {'Type': 'DIMENSION',
                 'Key': 'LINKED_ACCOUNT'}
            ]
        )

        data = response['ResultsByTime']
        for i in range(len(data)):
            try:
                groups = data[i]['Groups']
                startkey = data[i]['TimePeriod']['Start']

            except Exception as e:
                print(f'Early exception setting groups and startime: {e}')
                continue

            for g in range(len(groups)):
                try:
                    account_num = groups[g]['Keys'][0]
                    last5 = account_num[-5:]
                    account_num_clean = ('X'*7) + last5
                    cost = groups[g]['Metrics']['UnblendedCost']['Amount']
                    cost_u = groups[g]['Metrics']['UnblendedCost']['Unit']
                    usage = groups[g]['Metrics']['UsageQuantity']['Amount']
                    usage_u = groups[g]['Metrics']['UsageQuantity']['Unit']
                    month = startkey[0:7]
                except Exception as e:
                    print(f'Groups level exception: {e}')
                    continue
                idenity = f'{region}:{record_type}:{startkey}:{account_num}'
                print(f'writing dictionary entry for {idenity}')

                cost_int = int(float(cost))
                usage_int = int(float(usage))

                # write dict entries
                records.append({
                    'Record-Type': f'CE - {record_type}',
                    'Customer Name': os.environ['customer_name'],
                    'Billing Month': month,
                    'Region': 'All Regions',
                    'Account Number': account_num_clean,
                    f'Billed Cost ({cost_u})': f'{cost_int:.0f}',
                    f'Usage ({usage_u})': f'{usage_int:.0f}'
                })
                records.append({
                    'Record-Type': f'CE - {record_type}',
                    'Customer Name': os.environ['customer_name'],
                    'Billing Month': month,
                    'Region': region,
                    'Account Number': account_num_clean,
                    f'Billed Cost ({cost_u})': f'{cost_int:.0f}',
                    f'Usage ({usage_u})': f'{usage_int:.0f}'
                })

    return records


def convertJSON_S3(target_bucket, target_file_name, input_dict):
    if len(input_dict) > 0:
        body = json.dumps(input_dict)
        s3 = boto3.client('s3')
        print("Check s3 put", s3.put_object(Bucket=target_bucket,
                                            Key=target_file_name,
                                            Body=body))
