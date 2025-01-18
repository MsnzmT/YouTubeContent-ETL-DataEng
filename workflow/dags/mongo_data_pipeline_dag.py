from airflow import DAG
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.operators.python import PythonOperator
from datetime import datetime
from clickhouse_driver import Client
from airflow.models import Variable
import logging 

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Task to read from MongoDB
def read_from_mongo(**kwargs):
    try:
        # You can adjust the batch size in the Airflow UI without changing the code
        batch_size = int(Variable.get("mongo_batch_size", default_var=1000))
        mongo_hook = MongoHook(conn_id='MONGO_CONN_ID')
        client = mongo_hook.get_conn()
        db = client['videos']
        collection = db['videos']
        cursor = collection.find().batch_size(batch_size)

        batch_number = 0
        while cursor.alive:
            batch = []
            for i in range(batch_size):
                try:
                    doc = cursor.next()
                    doc['_id'] = str(doc['_id'])
                    batch.append(doc)
                except StopIteration:
                    break
            if batch:
                key = f'mongo_batch_{batch_number}' 
                kwargs['ti'].xcom_push(key=key, value=batch)
                # logger.info(f"Batch {batch_number} retrieved from MongoDB: {batch}")
                batch_number += 1

        logger.info(f"Total batches pushed to XCom: {batch_number}")

    except Exception as error:
        logger.error(f"Error extracting data from MongoDB, Batch {batch_number}, Error: {error}")
        raise

    finally:
        client.close()

# Task to create schema in ClickHouse
def create_clickhouse_schema():
    client = Client(host='clickhouse', user='airflow', password='airflow')
    
    # Create the database if it doesn't exist
    client.execute('CREATE DATABASE IF NOT EXISTS bronze')
    
    # Create a table in ClickHouse
    client.execute('''
    CREATE TABLE IF NOT EXISTS bronze.videos (
        id String,
        owner_username String,
        owner_id String,
        title String,
        tags Nullable(String),
        uid String,
        visit_count Int64,
        owner_name String,
        duration Int32,
        posted_timestamp Int32,
        comments Nullable(String),
        like_count Nullable(Int64),
        is_deleted Bool,
        created_at Int64,
        expire_at Int64,
        update_count Int32
    ) ENGINE = MergeTree() ORDER BY id
    ''')
    
    logger.info("ClickHouse schema created successfully.")
    client.disconnect()

# Task to load data into ClickHouse
def load_to_clickhouse(**kwargs):
    client = Client(host='clickhouse', user='airflow', password='airflow')
    batch_number = 0
    while True:
        key = f'mongo_batch_{batch_number}'
        mongo_batch = kwargs['ti'].xcom_pull(task_ids='read_from_mongo', key=key)
        if not mongo_batch:
            break  # Exit the loop if no more batches are found
        
        # Insert documents into ClickHouse
        client.execute('''
            INSERT INTO bronze.videos (
                    id, owner_username, owner_id, title, tags, uid, visit_count, owner_name, duration,
                    posted_timestamp, comments, like_count, is_deleted, created_at, expire_at, update_count
                ) VALUES
                    ''',
            [(doc['id'], doc['owner_username'], doc['owner_id'], doc['title'], doc.get('tags'),
              doc['uid'], doc['visit_count'], doc['owner_name'], doc['duration'], doc['posted_timestamp'],
              doc.get('comments'), doc.get('like_count'), doc['is_deleted'], doc['created_at'],
              doc['expire_at'], doc['update_count'])
             for doc in mongo_batch]
        )
        
        logger.info(f"Batch {batch_number} inserted into ClickHouse")
        batch_number += 1

    clickhouse_result = client.execute('SELECT count(*) FROM bronze.videos')
    logger.info("ClickHouse Result: %s", clickhouse_result)

    client.disconnect()



# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

with DAG('mongo_data_pipeline_dag', default_args=default_args, schedule_interval='@daily', catchup=False) as dag:
    read_task = PythonOperator(
        task_id='read_from_mongo',
        python_callable=read_from_mongo,
        provide_context=True,
    )

    create_schema_task = PythonOperator(
        task_id='create_clickhouse_schema',
        python_callable=create_clickhouse_schema,
    )

    load_task = PythonOperator(
        task_id='load_to_clickhouse',
        python_callable=load_to_clickhouse,
        provide_context=True,
    )

[read_task, create_schema_task] >> load_task

