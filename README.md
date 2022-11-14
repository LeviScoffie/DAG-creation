# DAG-creation

Prompts
    * Modify the DAG we created during the lessons ofr transferring yellow taxi data

    * Create a new dag for transferring FHV data

    * Create another dag for the Zones data


Head to data_ingestion_dag and change it a littel bit.

We will not be creating an external table now becasue we shall do that in another exercise so we will not need the `BigQueryCreateExternalTableOperator`

##### BacKFilling
Force run using airflow worker/webserver 

 1. docker ps 
 2. copy container id webserver 
 3. run `docker exec -it {container id} bash` 
 4. Run `airflow dags backfill {dag_name} --reset-dagruns -s {date to start} -e {end date}`