#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""

"""
import json
import logging
from .base import TestBase

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '21.08.13'


class TestGet(TestBase):
    """
        Test the result of some /get operations
    """

    def test_empty(self):
        """
            Test an empty query
        """

        tornado_data = self.curl_tornado('/api/persons')

        logging.debug(tornado_data)
        assert tornado_data == []

    def test_likefilter(self):
        """
            Test like something
        """

        filters = [dict(name='name', op='like', val='%r%')]
        params = dict(q=json.dumps(dict(filters=filters)))

        tornado_data = self.curl_tornado('/api/persons', params=params)

        assert len(tornado_data) == 2
        assert set(x['name'] for x in tornado_data) == {'Bernd', 'Feris'}

    def test_ascsorting(self):
        """
            Test sorting (ascending)
        """

        order_by = [dict(field='age', direction='asc')]
        params = dict(q=json.dumps(dict(order_by=order_by)))

        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(tornado_data)

        tornado_ages = [o['age'] for o in tornado_data]

        assert int(tornado_ages[0]) == 9
        assert int(tornado_ages[1]) == 13
        assert int(tornado_ages[2]) == 20

    def test_descsorting(self):
        """
            Test sorting (desscending)
        """

        order_by = [dict(field='age', direction='desc')]
        params = dict(q=json.dumps(dict(order_by=order_by)))

        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(tornado_data)

        tornado_ages = [o['age'] for o in tornado_data]

        assert int(tornado_ages[-1]) == 9
        assert int(tornado_ages[-2]) == 13
        assert int(tornado_ages[-3]) == 20

    def test_single(self):
        """
            Test for a specific persons per pk
        """

        tornado_data = self.curl_tornado('/api/persons/1')
        assert tornado_data['name'] == 'Anastacia'
        assert tornado_data['_id'] == 1
        assert tornado_data['cities'] == [{'_city': '60400', '_user': 1}]
        assert tornado_data['computers'] == [{'_id': 1, 'cpu': 3.2, 'ram': 4.0, '_user': 1}, {'_id': 2, 'cpu': 12.0, 'ram': 4.0, '_user': 1}]

    def test_float(self):
        """
            Test for a float value
        """
        tornado_data = self.curl_tornado('/api/computers')

        tornado_computer_cpu = tornado_data[0]['cpu']

        assert isinstance(tornado_computer_cpu, float)

    def test_results_per_page(self):
        """
            Test acknowledgment of parameter results_per_page
        """

        params = dict(results_per_page=2)

        tornado_data = self.curl_tornado('/api/persons', params=params)

        logging.debug(tornado_data)

        assert len(tornado_data) == 2

    def test_nothing(self):
        """
            Test for some missing data
        """

        self.curl_tornado('/api/persons/1337', assert_for=404)

    def test_relation(self):
        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 60400}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data) == 2

        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 10800}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data) == 1

        params = {
            'q': json.dumps({'filters': [{'name': 'cities._city', 'op': 'any', 'val': 123}]})
        }
        tornado_data = self.curl_tornado('/api/persons', params=params)
        assert len(tornado_data) == 0
