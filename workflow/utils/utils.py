import logging

import boto3
from datetime import datetime, timedelta
import pytz


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def connected_to_s3():
    endpoint_url = 'https://s3.ir-thr-at1.arvanstorage.ir'
    access_key = 'ab5fc903-7426-4a49-ae3e-024b53c30d27'
    secret_key = 'f70c316b936ffc50668d21442961339a90b627daa190cff89e6a395b821001f2'
    bucket_name = 'qbc'
    s3_resource = boto3.resource(
        's3', endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key,
    )

    return s3_resource, bucket_name


def get_new_files(start_date, file_extensions):
    """
    Retrieve new files from an S3 bucket that match the specified extensions and were created on the execution date.
    """
    s3_resource, bucket_name = connected_to_s3()
    bucket = s3_resource.Bucket(bucket_name)

    new_files = []

    # Calculate the date range for the execution date (e.g., files created on that day)
    tz = pytz.timezone('UTC')  # Adjust this to your desired timezone
    if start_date.tzinfo is None:
        start_date = tz.localize(start_date)

    logger.info(f'#### {start_date} - {type(start_date)}')
    # Iterate through all objects in the bucket
    for obj in bucket.objects.all():
        if any(obj.key.endswith(ext) for ext in file_extensions):
            file_last_modified = obj.last_modified
            if start_date <= file_last_modified:
                new_files.append(obj.key)

    return new_files


def safe_convert_datetime(value):
    """
    Convert a value to datetime.
    - If already a datetime, return as-is.
    - If string in ISO format, convert using `fromisoformat()`.
    - If string in MongoDB format (with 'T' separator), use `strptime()`.
    """
    if isinstance(value, datetime):
        return value  # Already a datetime object

    elif isinstance(value, str):
        try:
            # If string format is "YYYY-MM-DD HH:MM:SS", convert it
            if "T" in value:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)  # Handle invalid format gracefully

    return datetime(1970, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)