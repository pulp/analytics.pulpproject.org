This repo contains the backend code for:

* https://analytics.pulpproject.org/  - The production site is the [main branch](https://github.com/pulp/analytics.pulpproject.org)
* https://dev.analytics.pulpproject.org/  - The dev site is the [dev branch](https://github.com/pulp/analytics.pulpproject.org/tree/dev)


## Telemetry Data Flow

At a high level, the metrics data flows like this:

1. Pulpcore gathers and posts telemetry daily from each installation
2. The analytics site receives and stores the data without summarization
3. Once a day the data is summarized via a django command called on a cron job. This also cleans old
raw data after some time.
4. The charts on the site are visualized from the summary data


### Gathering and Submitting Data

Pulpcore installations gather the metrics and submit them to either the dev or prod site
depending on what the version strings of the pulp components are. If all version strings are
GA releases its sent to the production sent, otherwise it's sent to the dev site. See the
[get_telemetry_posting_url() code](https://github.com/pulp/pulpcore/blob/main/pulpcore/app/tasks/telemetry.py#L25).

Telemetry payload is submitted to the server via a [Protocol Buffer](https://developers.google.com/protocol-buffers/)
definition, which is defined [here](https://github.com/pulp/analytics.pulpproject.org/blob/main/telemetry.proto).
The pulpcore code gathers the telemetry data and constructs the telemetry payload
[in this module](https://github.com/pulp/pulpcore/blob/main/pulpcore/app/tasks/telemetry.py).

The protocol buffer definition is compiled locally with the commands below and checked-in
[here in this repo](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/telemetry_pb2.py)
and [here in pulpcore](https://github.com/pulp/pulpcore/blob/main/pulpcore/app/protobuf/telemetry_pb2.py).

```shell
sudo dnf install protobuf  # Install it anyway you want
cd analytics.pulpproject.org  # The command below assumes you are in the root dir
protoc --python_out pulpanalytics/ ./telemetry.proto  # Copy this to pulpcore also
```

### Storing Telemetry

The Telemetry data POST is [handled here](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/views.py#L171-L184)
using the protobuf object. The pieces are then saved as [model instances](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/models.py)
all of which foreign key to a single System object which stores the datetime of submission.

### Summarization

Summarization occurs when an openshift cron-job in the dev or prod site calls the following command
every 24 hours: `./manage.py summarize`. This executes
[this code](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/management/commands/summarize.py).

The summarize command uses a separate [protobuf definition](https://github.com/pulp/analytics.pulpproject.org/blob/main/summary.proto)
which can be compiled with commands below and stored [here](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/summary_pb2.py).

```shell
sudo dnf install protobuf  # Install it anyway you want
cd analytics.pulpproject.org  # The command below assumes you are in the root dir
protoc --python_out pulpanalytics/ ./summary.proto  # This only lives on the server side (this repo)
```

A summary is produced for each 24 hour period and stores it as json data in a
[DailySummary instance](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/models.py#L45).
How each telemetry metric is summarized is beyond the scope of this document, look at the code and
the proposals for each telemetry metric (which should outline summarization).


### Visualizing Summarized Data

Visualizing is done using [Chart.js](https://www.chartjs.org/) and is handled by this
[get view](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/views.py#L139-L169)
which uses [this template](https://github.com/pulp/analytics.pulpproject.org/blob/main/pulpanalytics/templates/pulpanalytics/index.html).
This goal of this code is to read all summary data and collate it into Chart.js data structures.


## Setting up a Dev Env

1. Create (or activate) a virtualenv for your work to live in:

```
python3 -m venv analytics.pulpproject.org
source analytics.pulpproject.org/bin/activate
```


2. Clone and Install Dependencies

```
git clone https://github.com/pulp/analytics.pulpproject.org.git
cd analytics.pulpproject.org
pip install -r requirements.txt
```


3. Start the database

I typically use [the official postgres container](https://hub.docker.com/_/postgres) with podman to
provide the database locally with the commands below (taken from 
[this article](https://mehmetozanguven.github.io/container/2021/12/15/running-postgresql-with-podman.html)).

Fetch the container with: `podman pull docker.io/library/postgres`. Afterwards you can see it listed
with `podman images`.

Start the container with: `podman run -dt --name my-postgres -e POSTGRES_PASSWORD=1234 -p 5432:5432 postgres`

Connect to the db with `psql` using `podman exec -it my-postgres bash`. Then connect with user
`postgres` which is the default of the postgres container. Here's a full example:

```
[bmbouter@localhost analytics.pulpproject.org]$ podman exec -it my-postgres bash
root@f70daa2ab15f:/# psql --user postgres
psql (14.5 (Debian 14.5-1.pgdg110+1))
Type "help" for help.

postgres=# \dt
Did not find any relations.
postgres=#
```

4. Configure the Python App to Use Postgresql

By default, the app uses environment variable for [database settings](https://github.com/pulp/analytics.pulpproject.org/blob/01c491eee833c8dc3513e3b56c2f349511bb162e/app/settings.py#L86-L90)
and [`SECRET_KEY`](https://github.com/pulp/analytics.pulpproject.org/blob/01c491eee833c8dc3513e3b56c2f349511bb162e/app/settings.py#L24).
Set these environment variables like this:

```
export DB_DATABASE="postgres"
export DB_USERNAME="postgres"
export DB_PASSWORD="1234"
export DB_HOST="localhost"
export APP_KEY="ceb0c58c-5789-499a-881f-410aec5e1003"
```

The APP_KEY is just a random string here.

5. Apply Migrations

Apply migrations with `./manage.py migrate`

6. Create a superuser (if you want to use the Admin site)

`./manage.py createsuperuser`

7. Run the server

`./manage.py runserver`

You can then load the page at `http://127.0.0.1:8000/` or the Admin site at
`http://127.0.0.1:8000/admin/`.


## Summarizing Data

Summarize data by calling `./manage.py summarize`.

This will not summarize data posted "today" because it's not a full summary yet, so for testing it
can be helpful to backdate data.


## Delete the DB and reapplying migrations

Stop and delete it with the commands below. Then restart the container and reapply migrations.

```
podman stop my-postgres
podman rm my-postgres
```

## Submitting and deploying PRs

The normal workflow is:

1. Develop your changes locally and open a PR against the `dev` branch.
2. Merge the PR, and after about 5ish minutes, your changes should show up at
   `https://dev.analytics.pulpproject.org/`.
3. Test your changes on the `https://dev.analytics.pulpproject.org/` site.
4. Open a PR that merges `dev` into `main`. When this is merged after 5ish minutes your changes
   should show up on `https://analytics.pulpproject.org/`.
