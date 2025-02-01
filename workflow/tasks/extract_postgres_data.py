from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from utils.load_sql_query import load_query_from_file


def extract_postgres_batch(batch_size, **context):
    last_processed_id = Variable.get("last_processed_id", default_var=0)
    query_file_path = "utils/extract_postgres.sql"
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    query = load_query_from_file(query_file_path)
    
    result = pg_hook.get_records(
        query,
        parameters=(last_processed_id, batch_size)
    )
    
    if result:
        Variable.set("last_processed_id", result[-1][0])
    else:
        return False
    context['ti'].xcom_push(key='batch_data', value=result)
