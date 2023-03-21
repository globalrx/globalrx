# Drug Label Explorer (DLE)

#### Overview

DrugLabelExplorer is a tool for searching drug labels. The system loads drug label data from the Federal Drug Administration [FDA](https://labels.fda.gov/) and the European Medicines Agency [EMA](https://www.ema.europa.eu/en/medicines) and stores these into a MariaDB database. Searches can performed against this database using the form provided on the website.

At the time of this writing, the latest version of the website is deployed at [druglabelexplorer.org](https://druglabelexplorer.org), which may or may not be available at the time you are reading this.

#### Features

Main features of DLE include:

- The ability to search drug labels from multiple sources
- The ability to compare different drug labels
- The ability to register as a user and load your own private drug labels

#### System

DLE is a web app written in Python using the [Django](https://www.djangoproject.com/) framework. The backend uses [MariaDB](https://mariadb.org/).

Additional information for the project is included in the [Latest Report](./docs/report.pdf)

For setup instructions see: [Setup](./docs/setup/readme.md)

Project slides are [Here](./docs/dle.pdf)

#### Design

We decide to use Searchkit

Searchkit to simplify using Elasticsearch for Search:

UI Search Components for React, Vue, Angular, and more
Searchkit Node API proxies Elasticsearch requests from the browser.
Ability to use Elasticsearch Query DSL for advanced queries

