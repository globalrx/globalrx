# GlobalRx

## Overview

GlobalRx is a tool for searching drug labels, created as part of the Harvard University Extension School Software Engineering Capstone course 2023. It builds upon the [Drug Label Explorer (DLE)](https://github.com/DrugLabelExplorer/dle) created by the 2022 course and extends that project to include additional label regions and new features.

### Data
GlobalRx currently includes labels from the following sources:
- [FDA - USA](https://labels.fda.gov/)
- [EMA - EU](https://www.ema.europa.eu/en/medicines)
These labels are parsed and stored in a Postgres database using Django models, then indexed into Elasticsearch for faster and more accurate search leveraging semantic and vector search capabilities.

### Features

Main features of GlobalRx include:

- The ability to search drug labels from multiple sources
- The ability to compare different drug labels
- The ability to register as a user and load your own private drug labels

### System

GlobalRx is a web app written in Python using the [Django](https://www.djangoproject.com/) framework. The backend uses Postgres and Elasticsearch for data storage and search. The frontend uses Django templates. The application is containerized using Docker for easy deployment and development.

### Setup

For GlobalRx setup instructions see: [Setup](./docs/readme.md)
The current database structure is avaiable via [DBVisualizer export](./docs/dbvisualizer.png)

#### DLE 2022
Due to changes, DLE 2022 may no longer work as originally designed. See [Drug Label Explorer (DLE)](https://github.com/DrugLabelExplorer/dle) for the original project. Some artifacts of that project are still available in this repository, but are not actively maintained.
- Additional information for DLE is included in the [2022 Report](./docs/dle/report.pdf)
- DLE setup instructions: [Setup](./docs/dle/setup/readme.md)
- 2022 project slides are [Here](./docs/dle/dle.pdf)

#### Design

We decide to use Searchkit

Searchkit to simplify using Elasticsearch for Search:

UI Search Components for React, Vue, Angular, and more
Searchkit Node API proxies Elasticsearch requests from the browser.
Ability to use Elasticsearch Query DSL for advanced queries

