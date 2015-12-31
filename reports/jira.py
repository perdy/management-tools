# -*- coding: utf-8 -*-
"""
Jira Reports.
"""
import os
from configparser import ConfigParser
from typing import List, Any, Dict

import datetime
import pandas as pd

from connectors.jira import JiraClient
from exceptions import ImproperlyConfigured

__all__ = ['JiraReport']


class JiraReport(object):
    def __init__(self, sprint: str = None, date_from: 'datetime.datetime' = None, date_to: 'datetime.datetime' = None,
                 usernames: List[str] = None):
        """
        Report initialization.

        :param sprint: Sprint name.
        :param date_from: Initial date to search.
        :param date_to: Ending date to search.
        :param usernames: Usernames.
        """
        if not sprint or not date_from or not date_to or not usernames:
            config = self._get_config()
            date_format = '%Y-%m-%d'

            sprint = config['sprint']
            date_from = datetime.datetime.strptime(config['date_from'], date_format)
            date_to = datetime.datetime.strptime(config['date_to'], date_format)
            usernames = config['usernames'].strip().replace(' ', '').split(',')

        self.sprint = sprint
        self.date_from = date_from
        self.date_to = date_to
        self.usernames = usernames

        # Jira Client
        self.client = JiraClient()

        # Custom fields
        self.custom_fields = self.client.custom_fields

    def _get_config(self) -> Dict[str, str]:
        """
        Gets config parameters.
        File: reports.conf

        :return: Config parameters.
        """
        parser = ConfigParser()
        parser.read(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'reports.conf')))

        # Get jira arguments
        try:
            jira = {option: parser.get('jira', option) for option in parser.options('jira')}
        except Exception as e:
            raise ImproperlyConfigured('jira') from e

        return jira

    def tasks(self) -> pd.DataFrame:
        """
        Report all tasks of a sprint. The fields included are:
        - Key.
        - Assignee.
        - Summary.
        - T-Shirt.
        - Story Points.
        - Original Estimate.
        - Time Spent.
        - Type.

        :return: Tasks.
        """

        def get_tasks_data(issue):
            fields = issue['fields']
            t_shirt = fields.get(self.custom_fields['t_shirt_size'], {}) or {}

            return {
                'Key': issue['key'],
                'Assignee': fields['assignee']['displayName'] if fields['assignee'] else None,
                'Summary': fields['summary'],
                'Type': fields['issuetype']['name'],
                'T-Shirt': t_shirt.get('value', None),
                'Story Points': fields.get(self.custom_fields['story_points'], None),
                'Original Estimate': fields['aggregatetimeoriginalestimate'] / 3600 if fields[
                    'aggregatetimeoriginalestimate'] else 0,
                'Time Spent': fields['aggregatetimespent'] / 3600 if fields['aggregatetimespent'] else 0,
            }

        included_fields = ('key', 'assignee', 'summary', self.custom_fields['story_points'], self.custom_fields['t_shirt_size'],
                           'aggregatetimeoriginalestimate', 'aggregatetimespent', 'issuetype')
        tasks = self.client.get_tasks(self.sprint, fields=included_fields)
        tasks_data = [get_tasks_data(t) for t in tasks['issues']] if tasks and 'issues' in tasks else []
        return pd.DataFrame.from_records(tasks_data, index='Key')

    def subtasks(self) -> Dict[str, Any]:
        """
        Report all subtasks of a sprint. The fields included are:

        :return: Subtasks.
        """

        def get_subtasks_data(issue):
            fields = issue['fields']
            resolution = fields.get('resolution', {}) or {}

            return {
                'Key': issue['key'],
                'Parent': fields['parent']['key'],
                'Summary': fields['summary'],
                'Type': fields['issuetype']['name'],
                'Status': fields['status']['name'],
                'Resolution': resolution.get('name', None),
                'Original Estimate': fields['aggregatetimeoriginalestimate'] / 3600 if fields[
                    'aggregatetimeoriginalestimate'] else 0,
                'Time Spent': fields['aggregatetimespent'] / 3600 if fields['aggregatetimespent'] else 0,
                'Assignee': fields['assignee']['displayName'] if fields['assignee'] else None,
            }

        subtasks = self.client.get_subtasks(self.sprint)
        subtasks_data = [get_subtasks_data(subtask) for subtask in subtasks]
        return pd.DataFrame.from_records(subtasks_data, index='Key')

    def worklogs(self) -> pd.DataFrame:
        """
        Report all worklogs for a given user.

        :return: Worklogs.
        """

        def get_worklogs_data(worklog):
            return {
                'Author': worklog['author']['displayName'],
                'Key': worklog['issue']['key'],
                'Issue': worklog['issue']['summary'],
                'Type': worklog['issue']['issueType']['name'],
                'Time Spent': worklog['timeSpentSeconds'] / 3600,
                'Comment': worklog['comment'],
            }

        worklogs = [w for u in self.usernames for w in self.client.get_worklogs(self.date_from, self.date_to, u)]
        worklogs_data = [get_worklogs_data(worklog) for worklog in worklogs]
        return pd.DataFrame.from_records(worklogs_data)
