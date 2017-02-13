# Prerequisites
This project runs on Linux and requires having Docker and python 2.7.

# Getting Started
create a venv, install Time-Sync client and hit `tsc --help`. 

# Usage Example
    adaml@adaml-LT:~$ tsc init -p ~/dev/time-sync
        Initializing Time-Sync CLI local env.
        Time-Sync CLI environment initialized successfully.
    adaml@adaml-LT:~$ tsc bootstrap
        Pulling required docker images..
        Starting Redis service container..
        waiting for redis service port on 172.17.0.2:6379
        Starting Rabbitmq service container..
        waiting for rabbitmq service port on 172.17.0.3:5672
        Failed connecting to 172.17.0.3 on 5672, Retrying in 3 seconds...
        Starting 4 client containers..
        Started new client at 172.17.0.4
        Started new client at 172.17.0.5
        Started new client at 172.17.0.6
        Started new client at 172.17.0.7
    adaml@adaml-LT:~$ tsc clients list 
        Found 4 clients in cluster:
        49dc422a-5e0e-42cf-8011-81e01bb44995
        94cbb51e-4d5b-4d73-9574-dea8a8b51cf6
        76f97238-a130-4c93-9f76-07a74f91af64
        da5fa50d-1e8a-489f-a664-39f37f0fd3b7
    adaml@adaml-LT:~$ tsc clients list -v
        Found 4 clients in cluster:
        Client ID: 49dc422a-5e0e-42cf-8011-81e01bb44995, IP Address 172.17.0.4, Time 1485069026.06, Master Client ID None
        Client ID: 94cbb51e-4d5b-4d73-9574-dea8a8b51cf6, IP Address 172.17.0.5, Time 1485069026.06, Master Client ID 49dc422a-5e0e-42cf-8011-81e01bb44995
        Client ID: 76f97238-a130-4c93-9f76-07a74f91af64, IP Address 172.17.0.6, Time 1485069025.35, Master Client ID 49dc422a-5e0e-42cf-8011-81e01bb44995
        Client ID: da5fa50d-1e8a-489f-a664-39f37f0fd3b7, IP Address 172.17.0.7, Time 1485069026.05, Master Client ID 49dc422a-5e0e-42cf-8011-81e01bb44995
    adaml@adaml-LT:~$ tsc clients add -n 3
        Starting 3 client containers..
        Started new client at 172.17.0.9
        Started new client at 172.17.0.10
        Started new client at 172.17.0.11
    adaml@adaml-LT:~$ tsc clients list 
        Found 7 clients in cluster:
        86b3d3e7-4ada-4d88-9506-55feca0c81da
        94cbb51e-4d5b-4d73-9574-dea8a8b51cf6
        76f97238-a130-4c93-9f76-07a74f91af64
        5b7b8f36-d47a-475c-9afa-71843ae0c285
        19851bef-a3b0-48fc-8b42-f3079bc004d1
        49dc422a-5e0e-42cf-8011-81e01bb44995
        da5fa50d-1e8a-489f-a664-39f37f0fd3b7
    adaml@adaml-LT:~$ tsc clients remove -c 49dc422a-5e0e-42cf-8011-81e01bb44995
        Attempting to remove client with ID 49dc422a-5e0e-42cf-8011-81e01bb44995
        Client at IP 172.17.0.4 removed successfully
    adaml@adaml-LT:~$ tsc clients tail -c da5fa50d-1e8a-489f-a664-39f37f0fd3b7

# Description
A time sync program consisting of a server and clients.
* The server runs on one machine, and connects to clients on different machines in the same network.
* Each client sends it's time to the server every second.
* The server chooses one client from all the clients, whose clock will be the master clock.
* The server sends the master clock to each client every second.
* In-case the master client does not send it's time for one minute, the server will choose a new client from the other clients to be the master clock.

# Architecture
## Client:
The client is made out of 2 threads, a consumer thread and a publishing thread:

1. Consuming thread - Consumes `master-client` updates published by the server.
2. Publishing thread - Publishes the client time to a predefined global messaging queue every second.

Upon startup, the client declares a new queue and binds it to an existing exchange to receive `master client` updates from the server.
Once started, the client will send out his time and other details, including the latest master details consumed from the queue it created, every second.

## Server:
The server consists out of a Celery distributed task queue, Rabbitmq message broker and a Redis in-memory cache.

1. Celery
Running 4 concurrent workers by default (configurable via CLI at bootstrap).
A Celery task scheduled to run every second and publish the `master client` time to all clients via a queue exchange.
A Task to consume client messages published to the `global clients queue` by clients.
2. Rabbitmq
 One message exchange to allow new clients to join the cluster.
 A queue for each of the clients.
3. Redis cache
 Holds the latest data on each of the clients.
 Holds a special key to keep track of current master.

## Flow:

### Client To Server Request:
A Client request consists out of these fields: Client ID, Client time, latest `master client` ID and latest `master client` time.

1. Message is published by the client to the `global clients queue`.
2. Message is consumed in the server by one of the 4 Celery workers.
3. Server saves the message in the Redis cache with an expiration time of 60 seconds.

### Server to Client Request:
The server publishes the `master client` details stored in the Redis cache. These details include the `master client's` ID, IP and time.

1. A Task is triggered by celery to publish the latest `master client` details.
2. The `master client` data is pulled from the Redis cache. If `master client` data does not exist (either `master client` expired or never elected):
  2.1 A New `master client` is elected according to 'Client with lowest IP'.
  2.2 If no clients found:  
    2.2.1 Skip `master client` data message publishing.
  2.3 Else if `master client` was found
    2.3.1 a message containing the `master client` data will be published to the message exchange to be consumed by all clients.

## Demo
For demo purposes, Docker is used to run these services in different containers with different IPs.
Once bootstrapped, the latest client and server versions are installed in the client/server containers, and logs are logged to `/tmp/ts_server_logs` and
`/tmp/ts_client_logs`. To start a small cluster and manage it, use the Time-Sync CLI. To avoid having the CLI running as sudo please run `sudo usermod -aG docker $USER`.

## Notes
First bootstrap may take a few minutes as the CLI pulls the required docker images from docker-hub.
In addition, clients and server may take a sec to boot since these are installed upon container startup.
