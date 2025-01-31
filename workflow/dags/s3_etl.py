import logging
import os
from datetime import datetime, timedelta

import pendulum
from airflow.decorators import dag, task
from tasks.etl_s3_to_mongodb import elt_json_to_mongodb
from utils.telegram_alert import notify_on_failure, notify_on_success, notify_on_retry
from clickhouse_driver import Client
from airflow.models import Variable

from tasks.etl_mongo_to_clickhouse import etl_mongo_to_clickhouse_task
from utils.telegram_alert import notify_on_failure, notify_on_success, notify_on_retry

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
    'depends_on_past': True,
    'on_failure_callback': notify_on_failure,
    'on_success_callback': notify_on_success,
    'on_retry_callback': notify_on_retry,
}

# DAG definition
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='DAG for incremental processing and backfilling',
    tags=["ETL", "Incremental Processing", "Backfilling"],
    schedule_interval='0 19 * * *',  # Daily at 7 PM
    catchup=True,  # Enable backfilling
    start_date=pendulum.now().subtract(days=5),
)

def s3_etl():
    etl_mongo_to_clickhouse_task = PythonOperator(
        task_id='etl_mongo_to_clickhouse',
        provide_context=True,
        python_callable=etl_mongo_to_clickhouse_task,
        op_kwargs={'db_name': 'videos', 'collection_name': 'videos'},
        dag=dag,
    )

    etl_mongo_to_clickhouse_task

# Instantiate the DAG
dag = s3_etl()
