import logging
import os
from datetime import datetime, timedelta
import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from tasks.etl_s3_to_mongodb import etl_json_to_mongodb
from clickhouse_driver import Client
from airflow.models import Variable
from tasks.etl_tracking_csv import create_tracking_table
from tasks.etl_mongo_to_clickhouse import etl_mongo_to_clickhouse
from utils.telegram_alert import notify_on_failure, notify_on_success, notify_on_retry
from tasks.etl_process_s3_csv import process_csv_files
from tasks.pg_to_clickhouse import transfer_data_in_batches

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DAG-level variables
DAG_ID = os.path.basename(__file__).replace(".py", "")

# Define the DAG
default_args = {
    'owner': 'airflow',
    'start_date': pendulum.now().subtract(days=5),  # Start date = 5 days ago
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': notify_on_failure,
    'on_success_callback': notify_on_success,
    'on_retry_callback': notify_on_retry,
}

# DAG definition
with DAG(
    DAG_ID,
    default_args=default_args,
    description='DAG for incremental processing and backfilling',
    tags=["ETL", "Incremental Processing", "Backfilling"],
    schedule_interval='0 19 * * *',  # Daily at 7 PM
    catchup=False,
) as dag:

    etl_json_to_mongodb_task = PythonOperator(
        task_id='etl_json_to_mongodb',
        provide_context=True,
        python_callable=etl_json_to_mongodb,
        op_kwargs={'db_name': 'videos', 'collection_name': 'videos'},
        dag=dag
    )

    etl_mongo_to_clickhouse_task = PythonOperator(
        task_id='etl_mongo_to_clickhouse',
        provide_context=True,
        python_callable=etl_mongo_to_clickhouse,
        op_kwargs={'db_name': 'videos', 'collection_name': 'videos'},
        dag=dag,
    )
    
    etl_process_s3_csv_task = PythonOperator(
        task_id='etl_csv_to_postgres',
        provide_context=True,
        python_callable=create_tracking_table,
        dag=dag,
    )
    
    process_s3_files = PythonOperator(
        task_id='process_s3_files',
        python_callable=process_csv_files,
        provide_context=True,
        dag=dag,
    )
    
    transfer_to_clickhouse = PythonOperator(
        task_id='transfer_data_to_clickhouse',
        python_callable=transfer_data_in_batches,
        provide_context=True,
        dag=dag,
    )


etl_json_to_mongodb_task >> etl_mongo_to_clickhouse_task
etl_process_s3_csv_task >> process_s3_files >> transfer_to_clickhouse
