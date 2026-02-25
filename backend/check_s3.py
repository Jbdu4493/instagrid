import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_S3_REGION", "eu-west-3")
)
bucket = os.environ.get("AWS_S3_BUCKET", "joe-bizet-instagrid")

try:
    s3.head_object(Bucket=bucket, Key="drafts/images/draft_48c5a01a_0.jpg")
    print("OBJECT EXISTS IN S3!")
except Exception as e:
    print("OBJECT DOES NOT EXIST:", e)

# Let's see what IS in the drafts/images/ prefix
response = s3.list_objects_v2(Bucket=bucket, Prefix="drafts/images/")
print("Files in drafts/images/:")
for obj in response.get('Contents', []):
    print(" -", obj['Key'])
