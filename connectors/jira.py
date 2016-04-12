# -*- coding: utf-8 -*-
"""
Jira Connector.
"""
import json
import os
from configparser import ConfigParser
from typing import Dict, Union, List, Tuple, Any, Sequence
from urllib import parse

import requests

from exceptions import ImproperlyConfigured, LoginException

__all__ = ['JiraResources', 'JiraConnector', 'JiraClient']


class HttpMethods(object):
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    DELETE = 'delete'


class JiraResources(object):
    LOGIN = 'auth/1/session'
    SEARCH = 'api/2/search'
    WORKLOGS = 'tempo-timesheets/3/worklogs'


class JiraConnector(object):
    def __init__(self, username: str = None, password: str = None, base_url: str = None):
        """
        Connector initialization.

        :param username: Jira API username.
        :param password: Jira API password.
        :param base_url: Jira Api base url.
        """
        self._username = username
        self._password = password
        try:
            base_url_parsed = parse.urlparse(base_url)
            scheme = 'https'
            netloc = base_url_parsed.netloc
            path = parse.urljoin(base_url_parsed.path, '/rest/')
            self._base_url = parse.urlunparse((scheme, netloc, path, '', '', ''))
        except:
            raise ImproperlyConfigured("Wrong url")

        with requests.Session() as s:
            self._session = s

    def _request(self, resource: str, method: str = HttpMethods.GET, params: Dict[str, str] = None,
                 data: Dict[str, str] = None, headers: Dict[str, str] = None,
                 cookies: Dict[str, str] = None) -> Union[Dict, List]:
        """
        Convenience method to do requests.

        :param resource: Jira resource.
        :param method: Http method.
        :param params: Http params.
        :param data: Data to be sent.
        :param headers: Http headers.
        :param cookies: Http cookies.
        :return: Json response.
        """
        url = parse.urljoin(base=self._base_url, url=resource)

        request_function = getattr(self._session, method, lambda *args, **kwargs: None)

        response = request_function(url, params=params, data=data, headers=headers, cookies=cookies)
        return response.json() if response._content else None

    def login(self) -> Tuple[str, str]:
        """
        Jira login and return active session.

        :return: Active session.
        """
        # Prepare request
        body = json.dumps({'username': self._username, 'password': self._password})
        headers = {'content-type': 'application/json'}
        response = self._request(resource=JiraResources.LOGIN, method=HttpMethods.POST, data=body, headers=headers)

        try:
            session = response['session']['name'], response['session']['value']
        except KeyError:
            raise LoginException

        return session

    def logout(self):
        """
        Jira logout.
        """
        self._request(resource=JiraResources.LOGIN, method=HttpMethods.DELETE)

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 1000, fields: Sequence[str] = None,
                      expand: str = None) -> List[Any]:
        """
        Search issues using JQL.

        :param jql: Query in JQL.
        :param start_at: If paginated, which will be the first result to retrieve.
        :param max_results: If paginated, number of results to retrieve.
        :param fields: Fields to retrieve.
        :param expand: Fields to expand.
        :return: Found issues.
        """
        data = {
            'jql': jql,
            'startAt': start_at,
            'maxResults': max_results
        }

        if fields is not None:
            data.update({'fields': fields})

        if expand is not None:
            data.update({'expand': expand})

        body = json.dumps(data)
        headers = {'content-type': 'application/json'}
        response = self._request(resource=JiraResources.SEARCH, method=HttpMethods.POST, data=body, headers=headers)

        return response

    def worklogs(self, date_from: 'datetime.datetime', date_to: 'datetime.datetime', username: str,
                 project_key: str = None) -> List[Any]:
        """
        Search worklogs.

        :param date_from: Initial date to search.
        :param date_to: Ending date to search.
        :param username: Username.
        :param project_key: Project key.
        :return: Worklogs.
        """
        params = {
            'dateFrom': date_from.strftime("%Y-%m-%d"),
            'dateTo': date_to.strftime("%Y-%m-%d"),
            'username': username,
        }

        if project_key is not None:
            params.update({'projectKey': project_key})

        response = self._request(resource=JiraResources.WORKLOGS, method=HttpMethods.GET, params=params)

        return response

    def __enter__(self):
        self.login()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()


class JiraClient(object):
    def __init__(self, username: str = None, password: str = None, base_url: str = None):
        """
        Connector initialization.

        :param username: Jira API username.
        :param password: Jira API password.
        :param base_url: Jira Api base url.
        """
        config = self._get_config()

        if not username or password is None or not base_url:
            username = config['connection']['username']
            password = config['connection']['password']
            base_url = config['connection']['base_url']

        # Create Jira connector
        self._connector = JiraConnector(username, password, base_url)

        # Jira queries
        self._queries = config['queries']

        # Custom fields
        self.custom_fields = config['custom_fields']

    def _get_config(self) -> Dict[str, Dict[str, str]]:
        """
        Gets config parameters.
        File: jira.conf

        :return: Config parameters.
        """
        parser = ConfigParser()
        parser.read(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'jira.conf')))

        # Get connection parameters
        try:
            connection = {option: parser.get('connection', option) for option in parser.options('connection')}
        except Exception as e:
            raise ImproperlyConfigured() from e
        else:
            for opt in ['username', 'password', 'base_url']:
                if opt not in connection.keys():
                    raise ImproperlyConfigured('Connection parameter "{}" not found'.format(opt))

        # Get queries
        try:
            queries = {option: parser.get('queries', option) for option in parser.options('queries')}
        except Exception as e:
            raise ImproperlyConfigured('queries') from e

        config = {
            'connection': connection,
            'queries': queries,
        }

        # Get custom fields
        if 'custom_fields' in parser:
            try:
                fields = {option: parser.get('custom_fields', option) for option in parser.options('custom_fields')}
                config['custom_fields'] = fields
            except Exception as e:
                raise ImproperlyConfigured('custom_fields') from e

        return config

    def _get_tasks(self, jql, get_data, fields: Sequence[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Gets all tasks given JQL.

        :param jql: JQL.
        :param get_data: Function to extract data from retrieved JSON.
        :param fields: Tasks fields.
        :param kwargs: Query format args.
        :return: Tasks.
        """
        data = []
        start_at = 0
        max_results = 1000
        end = False
        with self._connector:
            while not end:
                tasks = self._connector.search_issues(jql, start_at=start_at, max_results=max_results, fields=fields)
                total = int(tasks['total'])
                end = start_at + max_results > total
                start_at += max_results + 1
                data.extend([get_data(t) for t in tasks['issues']] if tasks and 'issues' in tasks else [])

        return data

    def get_resolution_tasks(self, get_data, fields: Sequence[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get all tasks of a sprint.

        :param get_data: Function to extract data from retrieved JSON.
        :param fields: Tasks fields.
        :param kwargs: Query format args.
        :return: Tasks.
        """
        jql = self._queries['resolution_tasks'].format(**kwargs)
        return self._get_tasks(jql, get_data, fields, **kwargs)

    def get_sprint_tasks(self, get_data, fields: Sequence[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get all tasks of a sprint.

        :param get_data: Function to extract data from retrieved JSON.
        :param fields: Tasks fields.
        :param kwargs: Query format args.
        :return: Tasks.
        """
        jql = self._queries['sprint_tasks'].format(**kwargs)
        return self._get_tasks(jql, get_data, fields, **kwargs)

    def get_sprint_subtasks(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all tasks of a sprint.

        :param kwargs: Query format args.
        :return: List of subtasks.
        """
        jql = self._queries['subtasks'].format(**kwargs)
        included_fields = ('key', 'parent', 'assignee', 'summary', 'aggregatetimeoriginalestimate',
                           'aggregatetimespent', 'issuetype', 'resolution', 'status')

        with self._connector:
            tasks = self._connector.search_issues(jql, fields=included_fields)

        return [t for t in tasks['issues']]

    def get_worklogs(self, date_from: 'datetime.datetime', date_to: 'datetime.datetime',
                     username: str, project_key: str = None) -> List[Dict[str, Any]]:
        """
        Get all worklogs for given user.

        :param date_from: Initial date to search.
        :param date_to: Ending date to search.
        :param username: Username.
        :param project_key: Project key.
        :return: Worklogs.
        """
        with self._connector:
            tasks = self._connector.worklogs(date_from, date_to, username, project_key)

        return tasks


