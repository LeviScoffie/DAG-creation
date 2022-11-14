import os
import logging
from datetime import datetime


from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

## FROM THE REQUIREMENTS INSTALLED THROUGH THE requirements.txt file when build docker conatiner.
from google.cloud import storage #to interact with gcs storage

from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator # to interact with bigquery ino
#inorder to create an external table
import pyarrow.csv as pv # convert dataset into parquet before converted to gcs. but not needed since already in parquet.
import pyarrow.parquet as pq


#import some values from env variables in docker-compose .yml setup into our local variables.
PROJECT_ID= os.environ.get("GCP_PROJECT_ID")
BUCKET= os.environ.get("GCP_GCS_BUCKET")

AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME","/opt/AIRFLOW/")


def format_to_parquet (src_file , dest_file):
    if not src_file.endswith('.csv'):
        logging.error("Can only accept source files in csv format, for the moment")
        return
    
    table = pv.read_csv(src_file)
    pq.write_table(table, dest_file)
    
    
    

def upload_to_gcs (bucket, object_name, local_file):
    
    """
    Ref: from gcs to include linke
    :param bucket: GCS bucket name
    :param object_name: target path & file_name
    :param local_file : source path & file_name
    
    :return:
    """
    
    # WORKAROUND to prevent timeout for files > 6MB on 888kbps upload speed
    # ref googleapis/python/github.com
    # storage.blob._MAX_MULTIPART_SIZE= 5 * 1024 * 1024 #5mb
    
    # storage.blob._DEFAULT_CHUNKSIZE= 5 * 1024 * 1024 #5mb
    # #END OF WORKAROUND
    
    # if BUCKET:
    #     STATICFILES_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
        
    client = storage.Client() # creates a client for gcs storage
    bucket = client.bucket(bucket) # attaches itself to a bucket that u are passing as an input
    
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file) # uploads file that it is supposed to uplooad to a target location
    
    
    
  #ref:  
default_args = {
    "owner": "airflow",
    #"start_date": days_ago(1),
    "depends_on_past": False,
    "retries": 1,
    
    
}


def download_upload_gcp(
    
    dag,
    url_template,
    local_csv_path_template,
    local_parquet_path_template,
    local_gcp_path_template,
):
    
    with dag:
        download_dataset_task = BashOperator (
            task_id="download_dataset_task",
            bash_command =f"curl -sSLf {url_template} > {local_csv_path_template}"
            
        )
        
        format_to_parquet_task= PythonOperator(
            task_id="format_to_parquet_task",
            python_callable=format_to_parquet,
            op_kwargs={
                "src_file": local_csv_path_template,
                "dest_file": local_parquet_path_template
            },
        )
 
        local_to_gcs_task = PythonOperator (
            task_id  ="local_to_gcs_task",
            python_callable =upload_to_gcs,
            op_kwargs ={
                "bucket": BUCKET,
                "object_name": local_gcp_path_template,
                "local_file": local_parquet_path_template,
            },
            
        )

        rm_task = BashOperator (
            task_id="rm_task",
            bash_command =f"rm {local_csv_path_template} {local_parquet_path_template}"
          
        )
        download_dataset_task >> format_to_parquet_task >> local_to_gcs_task >> rm_task
        
    # https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv
    
ZONES_URL_TEMPLATE=" https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv"
ZONES_CSV_FILE_TEMPLATE=AIRFLOW_HOME +'/taxi_zone_lookup.csv'
ZONES_PARQUET_FILE_TEMPLATE= AIRFLOW_HOME +'/taxi_zone_lookup.parquet'
ZONES_GCP_PATH_TEMPLATE="raw/taxi_zone/taxi_zone_lookup.parquet"

zones_data_dag= DAG(
    dag_id = "zones_data_v1",
    schedule_interval = "@once",
    start_date=days_ago(1),
    default_args =default_args,
    catchup = True, #helps us go back in history
    max_active_runs = 3,
    tags= ["dtc-de"],
    
) 
    
download_upload_gcp(
        
        dag=zones_data_dag
        ,url_template= ZONES_URL_TEMPLATE
        ,local_csv_path_template=ZONES_CSV_FILE_TEMPLATE
        ,local_parquet_path_template=ZONES_PARQUET_FILE_TEMPLATE
        ,local_gcp_path_template=ZONES_GCP_PATH_TEMPLATE
    )
    
