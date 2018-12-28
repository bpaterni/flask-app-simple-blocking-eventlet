# flask-app-simple-blocking-eventlet

This app combines a few different blocking (busy) APIs that take some amount of time to service. To simulate long running database queries, I supply the database backend with a query to generate a long sequence of numbers. The sequence range may need to be adjusted for the desired amount of 'busy' time.

I've done some work to hopefully make this demo app easy to use, but unfortunately, there is some setup involved. To run the various database querying APIs. you'll need access to postgres, SQL Server, and Oracle databases. For this, I've found the use of docker containers to helpful:

* https://hub.docker.com/_/postgres/
* https://docs.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-2017
* https://hub.docker.com/_/oracle-database-enterprise-edition

Also, to connect to a SQL Server database, the ODBC client driver from Microsoft is required:

* https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-2017

