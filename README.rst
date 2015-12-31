================
Management Tools
================

:Version: 0.1.0
:Status: Production/Stable
:Author: José Antonio Perdiguero López

A set of tools to improve efficiency in team management tasks.

Quick start
===========

#. Clone this package::

    git clone https://github.com/PeRDy/management-tools

#. Install requirements in a virtualenv::

    pip install -r requirements.txt

#. Create config files to define the minimum set of parameters used::

    jira.conf
    reports.conf

Config files
============

This application includes an example of each config file used named as *foo.conf.example*. These files must be filled and
renamed to *foo.conf*.

Export reports
==============

To export reports made using IPython notebooks use the follow command::

    ipython nbconvert templates/reports/sprint_report.ipynb --to html --template templates/utils/hide_input.tpl
