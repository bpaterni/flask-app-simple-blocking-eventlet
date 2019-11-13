# flask-app-simple-blocking-eventlet

This app combines a few different blocking (busy) APIs that take some amount of time to service. To simulate long running database queries, I supply the database backend with a query to generate a long sequence of numbers. The sequence range may need to be adjusted for the desired amount of 'busy' time.

I've done some work to hopefully make this demo app easy to use, but unfortunately, there is some setup involved. To run the various database querying APIs. you'll need access to postgres, SQL Server, and Oracle databases. For this, I've found the use of docker containers to helpful:

* https://hub.docker.com/_/postgres/
* https://docs.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-2017
* https://hub.docker.com/_/oracle-database-enterprise-edition

Also, to connect to a SQL Server database, the ODBC client driver from Microsoft is required:

* https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-2017

## Usage

Once database dependencies are acquired, you should be ready to start running tests with the app. For example, within the project directory:

    ## ***Not required if connecting to an existing db or an already running database container
    ## Start dockerized SQL Server
    $ ./start-mssql
    ##
    ## Launch the flask app
    $ ./launch_app_local.sh


    ## Begin hitting the app with requests.
    ## For example, from a different terminal, using GNU parallel:
    $ seq 5 | parallel -j0 "curl -s localhost:5000/api/busy/mssql && echo {}"
