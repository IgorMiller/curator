from datetime import datetime, timedelta
from unittest import TestCase
from mock import Mock

import curator


class TestUtils(TestCase):
    def test_get_index_time(self):
        for text, datestring, dt in [
            ('2014.01.19', '%Y.%m.%d', datetime(2014, 1, 19)),
            ('2014-01-19', '%Y-%m-%d', datetime(2014, 1, 19)),
            ('2010-12-29', '%Y-%m-%d', datetime(2010, 12, 29)),
            ('2012-12', '%Y-%m', datetime(2012, 12, 1)),
            ('2011.01', '%Y.%m', datetime(2011, 1, 1)),
            ('2014-28', '%Y-%W', datetime(2014, 7, 14)),
            ('2010.12.29.12', '%Y.%m.%d.%H', datetime(2010, 12, 29, 12)),
                ]:
            self.assertEqual(dt, curator.get_index_time(text, datestring))

class TestShowIndices(TestCase):
    def test_show_indices(self):
        client = Mock()
        client.indices.get_settings.return_value = {
            'prefix-2014.01.03': True,
            'prefix-2014.01.02': True,
            'prefix-2014.01.01': True
        }
        indices = curator.get_indices(client, prefix='prefix-')

        self.assertEquals([
                'prefix-2014.01.01',
                'prefix-2014.01.02',
                'prefix-2014.01.03',
            ],
            indices
        )

class TestExpireIndices(TestCase):
    def test_all_daily_indices_found(self):
        client = Mock()
        client.indices.get_settings.return_value = {
            'prefix-2014.01.03': True,
            'prefix-2014.01.02': True,
            'prefix-2014.01.01': True,
            'prefix-2013.12.31': True,
            'prefix-2013.12.30': True,
            'prefix-2013.12.29': True,

            'prefix-2013.01.03': True,
            'prefix-2013.01.03.10': True,
            'prefix-2013.01': True,
            'prefix-2013.12': True,
            'prefix-2013.51': True,
        }
        index_list = curator.get_object_list(client, prefix='prefix-')
        expired = curator.find_expired_data(object_list=index_list, time_unit='days', older_than=4, prefix='prefix-', timestring='%Y.%m.%d', utc_now=datetime(2014, 1, 3))
        
        expired = list(expired)

        self.assertEquals([
                'prefix-2013.01.03',
                'prefix-2013.12.29',
                'prefix-2013.12.30',
            ],
            expired
        )

    def test_size_based_finds_indices_over_threshold(self):
        client = Mock()
        client.indices.status.return_value = {
            'indices': {
                'logstash-2014.02.14': {'index': {'primary_size_in_bytes': 3 * 2**30}},
                'logstash-2014.02.13': {'index': {'primary_size_in_bytes': 2 * 2**30}},
                'logstash-2014.02.12': {'index': {'primary_size_in_bytes': 1 * 2**30}},
                'logstash-2014.02.11': {'index': {'primary_size_in_bytes': 3 * 2**30}},
                'logstash-2014.02.10': {'index': {'primary_size_in_bytes': 3 * 2**30}},
            }
        }
        expired = curator.find_overusage_indices(client, disk_space=6)
        expired = list(expired)

        self.assertEquals(
            [
                ('logstash-2014.02.11', 0),
                ('logstash-2014.02.10', 0),
            ],
            expired
        )
