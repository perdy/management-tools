# -*- coding: utf-8 -*-
"""
Jira Connector.
"""
import json
import logging
from enum import Enum
from typing import Dict, Union, List, Tuple, Any, Sequence, Callable, AsyncIterable
from urllib import parse

import requests

from client.base import BaseClient
from exceptions import ImproperlyConfigured, LoginException

__all__ = ['Resource', 'Client']

logger = logging.getLogger(__name__)


class Resource(Enum):
    LOGIN = 'auth/1/session'
    SEARCH = 'api/2/search'
    WORKLOGS = 'tempo-timesheets/3/worklogs'


class Client(BaseClient):
    MAX_TRIES = 5

    def __init__(self, username: str, password: str, url: str, *args, **kwargs):
        """
        Connector initialization.

        :param username: Jira account username.
        :param password: Jira account password.
        :param url: Jira base url.
        """
        super(Client, self).__init__(*args, **kwargs)

        self._username = username
        self._password = password
        self.token = None
        try:
            base_url_parsed = parse.urlparse(url)
            scheme = 'https'
            netloc = base_url_parsed.netloc
            path = parse.urljoin(base_url_parsed.path, '/rest/')
            self._base_url = parse.urlunparse((scheme, netloc, path, '', '', ''))
        except:
            raise ImproperlyConfigured('Wrong url')

        with requests.Session() as s:
            self._session = s

    async def request(self, resource: str, method: str = 'get', params: Dict[str, str] = None,
                      data: Dict[str, str] = None, headers: Dict[str, str] = None,
                      cookies: Dict[str, str] = None) -> Union[Dict[str, Any], List]:
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

        logger.info('Response %s from %s.', response.status_code, url)
        logger.debug('Request parameters: %s', str(params))
        logger.debug('Request data: %s', str(data))
        logger.debug('Request headers: %s', str(headers))
        logger.debug('Request cookies: %s', str(cookies))

        return response.json() if response._content else None

    async def login(self) -> Tuple[str, str]:
        """
        Jira login and return active session.

        :return: Active session.
        """
        if not self.token:
            tries = 0
            session = None

            while not session:
                # Prepare request
                body = json.dumps({'username': self._username, 'password': self._password})
                headers = {'content-type': 'application/json'}
                response = await self.request(resource=Resource.LOGIN.value, method='post', data=body, headers=headers)

                try:
                    if 'session' not in response:
                        raise LoginException('Wrong username or password')
                    session = response['session']['name'], response['session']['value']
                except KeyError:
                    tries += 1
                    logger.debug('Cannot login. Retry %d/%d', tries, self.MAX_TRIES)
                    if tries >= self.MAX_TRIES:
                        raise LoginException('Cannot login')

            return session

    async def logout(self):
        """
        Jira logout.
        """
        if self.token:
            await self.request(resource=Resource.LOGIN.value, method='delete')
            self.token = None

    async def _search(self, jql: str, start_at: int = 0, max_results: int = 1000, fields: Sequence[str] = None,
                      expand: str = None) -> Union[Dict[str, Any], List]:
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
            data['fields'] = fields

        if expand is not None:
            data['expand'] = expand

        body = json.dumps(data)
        headers = {'content-type': 'application/json'}
        return await self.request(resource=Resource.SEARCH.value, method='post', data=body, headers=headers)

    async def search(self, jql: str, fields: Sequence[str] = None,
                     transform: Callable[[Dict[str, Any]], Dict[str, Any]] = lambda x: x,
                     **kwargs) -> AsyncIterable[Dict[str, Any]]:
        """
        Search issues using JQL, iterating over paginated responses and composing a full list of items.

        :param jql: JQL.
        :param transform: Function to transform data from retrieved JSON.
        :param fields: Tasks fields.
        :param kwargs: Query format args.
        :return: Tasks.
        """
        tasks = await self._search(jql, fields=fields)

        try:
            total = int(tasks['total'])
            start_at = int(tasks['startAt'])
            max_results = int(tasks['maxResults'])

            while start_at < total:
                for task in tasks.get('issues', []):
                    yield transform(task)

                start_at += max_results + 1
                tasks = await self._search(jql, start_at=start_at, max_results=max_results, fields=fields)
        except KeyError:
            logger.error('Invalid response: %s', str(tasks))

    async def worklogs(self, date_from: 'datetime.datetime', date_to: 'datetime.datetime', username: str,
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
            params['projectKey'] = project_key

        return await self.request(resource=Resource.WORKLOGS.value, method='get', params=params)

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
