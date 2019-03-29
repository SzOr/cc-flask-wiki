Cloud Computing - ECS781P - mini-project by Szczepan Orlowski (110291051).

## Flask-Cassandra-Wikimedia API Web-app 

[TOC]



### Synopsis

This app built with Flask allows the user to type in their query and pull the summary of the entry from Wikimedia API (extract from JSON object). Cassandra, residing on the same cluster, saves each pair of query and result that has not been entered before. If the query is repeated by a user, the information is pulled from Cassandra database rather than from Wikimedia API.



### File structure

- /static:

  - bootstrap.min.css -> styles

- /templates:

  - form.html -> form

- app.py  -> core script with extensive comments

- cassandra-peer-service.yml -> headless service allowing identifying IP of Cassandra nodes (from the lab)

- cassandra-replication-controller.yml -> managing replications of Cassandra (from the lab)

- cassandra-service.yml -> specifying metada such as name and port (from the lab)

- config.py -> containing SECRET_KEY overwritten by the config.py file in /instance, which is ignored by git

- Dockerfile -> responsible for building the image before deploying to gcloud repository and then to the Kubernetes cluster

- exists.txt -> I/O static file for verifying whether the Keyspace and the table have been created.

- requirements.txt -> contains the dependencies

  

### Dependencies

From *requirements.txt* 

```
pip==10.0.1
Click==7.0
Jinja2==2.10
Flask==1.0.2
MarkupSafe==1.1.1
WTForms==2.2.1
certifi==2019.3.9
chardet==3.0.4
idna==2.8
itsdangerous==1.1.0
Werkzeug==0.15.1
requests==2.21.0
setuptools==39.1.0
urllib3==1.24.1
cassandra-driver==3.17.0
```



### Deployment steps

In the process I followed Lab sheets from weeks 9 & 10 so I have not created any of the following steps just reshuffled them as I was trying to adjust them to the context of my application. In order to proceed with the below steps we need to create a project and pull the repository https://github.com/SzOr/cc-flask-wiki.git

#### Core steps

0. Directly after pulling the repository, please insert into config.py your key (I kept mine in /instance/config.py, which was included in .gitignore hence not pushed to the repository)

    ```
    SECRET_KEY = 'VALUE' 
    ```

1. Making sure we are working on the right project: 

   ```
   gcloud config set project project-name.
   ```

2. Setting the environment variable we will use for the rest of the process:

   ```
   export PROJECT_ID="$(gcloud config get-value project -q)"
   ```

3. Set the compute zone for the session.

   ```
   gcloud config set compute/zone us-central1-b
   ```

4. Enable the Container API.

   ```
   gcloud services enable container.googleapis.com
   ```

5. Build the Docker image from the Dockerfile

   ```
   docker build -t gcr.io/${PROJECT_ID}/flask-cassandra:v1 .
   ```

6. Configure the docker image

   ```
   gcloud auth configure-docker
   ```

7. Push the docker image into Google Cloud Container as an app

   ```
   docker push gcr.io/${PROJECT_ID}/flask-cassandra:v1
   ```

8. Create Gcloud container cluster (to be then managed via Kubernetes). 2 nodes will be used by Cassandra, 1 by our flask app.

   ```
   gcloud container clusters create cassandra --num-nodes=4
   ```

9. Download Cassandra image via Docker.

   ```
   docker pull cassandra:latest
   ```

10. Deploy and configure Cassandra using .yml files from the W10 lab.

    ```
    kubectl create -f cassandra-peer-service.yml
    kubectl create -f cassandra-service.yml
    kubectl create -f cassandra-replication-controller.yml
    ```

11. Scale Cassandra to as many replicas as necessary, we will keep it on one for now:

    ```
    kubectl scale rc cassandra --replicas=1 
    ```

12. Running the flask app in another Kubernetes pod and setting its port.

    ```
    kubectl run flask-app --image=gcr.io/${PROJECT_ID}/flask-cassandra:v1 --port=8080
    ```

13. Exposing the port of the app using LoadBalancer, it matches what is stated in Dockerfile and in the app.run of the app.py script

    ```
    kubectl run flask-app --image=gcr.io/${PROJECT_ID}/flask-cassandra:v1 --port=8080
    ```

14. [OPTIONAL] A string 'started' is written into exists.txt file once the app.py creates the Keyspace as well as the table that our flask app uses. If the file is not there or is not empty, following commands have to be run.

    To check the name of the Cassandra pod.

    ```
    kubectl get pods -l name=cassandra
    ```

    Then we need to enter the CQLSH:

    ```
    kubectl exec -it cassandra-123ab cqlsh
    ```

    Create the Keyspace and the Table.

    ```
    CREATE KEYSPACE wikiflask WITH REPLICATION = {'class' : 'SimpleStrategy', 'replication_factor' : 1};
    USE wikiflask;
    CREATE TABLE ask(ask_query text, ask_result text, PRIMARY KEY(ask_query));
    DESCRIBE keyspaces;
    ```

15. Now users can be sure everything is operational. To find the IP of our flask app:

    ```
    kubectl get services
    ```

16. Copy the  IP from the External column and run it in the browser.

    

    #### Additional step:

17. Depending on the user demand, replication-controller allows us to scale the Cassandra ring, there could be as many replicas as the cluster allows for:

    ```
    kubectl scale rc cassandra --replicas=Num
    ```



### Notes

Since I struggled to get Cassandra to work with Flask on Kubernetes, at the lab of week 12 I presented the prototype of the app that was essentially doing the same thing but locally, using SQLAlchemy database. I was asked to make a note of the fact that I will submit an app that is connected to Cassandra.

I am very grateful for support from the module leaders, particularly to Dr Felix Cuadrado who responded to many of my e-mails and agreed to meet me in-between the W12 lab and the deadline. After that meeting I was able to understand the [Cassandra documentation](https://datastax.github.io/python-driver/api/cassandra) better and hence complete the assignment using cassandra-driver's statements.  

I now want to develop the app further! First thing I would start from is splitting the app into more classes and configure Cassandra in a separate script file using methods checking if the Table exists, such as [here](https://datastax.github.io/python-driver/_modules/cassandra.html#AlreadyExists). I would enable HTTPS access and, out of curiosity, I would also attempt to encrypt the stored data.

