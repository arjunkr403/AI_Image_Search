import boto3
from app.config import settings

s3= boto3.client(
    "s3",
    endpoint_url=settings.R2_ENDPOINT,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto",
)

def upload_file(file_obj,key:str, content_type: str):

    # [file object] → R2 bucket → stored as "key"
    s3.upload_fileobj(
        file_obj,
        settings.R2_BUCKET,
        key,
        ExtraArgs={"ContentType":content_type}
    )
    
def delete_file(key: str):
    s3.delete_object(
        Bucket=settings.R2_BUCKET,
        Key=key,
    )