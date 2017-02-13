import logging
import os
import pickle

import redis

from time_sync.constants import (REDIS_HOST_IP_ENV,
                                 REDIS_PORT)
from utils import create_logger

REDIS_HOST_IP = os.getenv(REDIS_HOST_IP_ENV)
_MAX_CLIENT_IP = '255.255.255.255'

MASTER_CLIENT_ID_KEY = 'master_client_id_key'
CLIENT_MESSAGE_TIMEOUT = 60


class RedisClient(object):
    def __init__(self, redis_host=None):
        redis_host = redis_host or REDIS_HOST_IP
        self.cache = redis.Redis(host=redis_host, port=REDIS_PORT)
        self.logger = create_logger('redis_logger',
                                    level=logging.INFO)

    def get_master_data(self):
        mid, m_data = self.get_master_id()
        return pickle.loads(m_data)

    def get_master_ip(self):
        return self.get_master_data().get('ip')

    def get_master_time(self):
        return self.get_master_data().get('master_time')

    def get_master_id(self):
        mid = self.cache.get(MASTER_CLIENT_ID_KEY)
        if mid:
            master_data = self.cache.get(mid)
            if master_data:
                self.logger.debug('master id is {}'.format(mid))
                return mid, master_data
        return None, pickle.dumps({})

    def is_master(self, cid):
        return cid == self.cache.get(name=MASTER_CLIENT_ID_KEY)

    def set_client_data(self, data):
        self.cache.set(data['id'],
                       pickle.dumps(data),
                       ex=CLIENT_MESSAGE_TIMEOUT)

    def elect_leader(self):
        leader = self._elect_leader()
        if leader:
            self.cache.set(MASTER_CLIENT_ID_KEY, leader['id'])
        return leader

    def _elect_leader(self):
        self.logger.info('electing master client..')
        clients = self.get_all_clients()
        return self._elect_client_with_lowest_ip(clients)

    def get_all_clients(self):
        # todo: checkout pattern matching for UUID with cache.keys().
        # todo: Also pickling her not totally safe.
        return [pickle.loads(self.cache.get(name=key)) for key
                in self.cache.keys() if key != MASTER_CLIENT_ID_KEY]

    @staticmethod
    def _elect_client_with_lowest_ip(clients):
        # Since 'cache.keys()' result is ordered, this function will return
        # the same result for all workers as best as possibly can.
        client_ip = _MAX_CLIENT_IP
        client_data = None
        for client in clients:
            # Not supporting ipV6 :)
            if int(client['ip'].replace('.', '')) < \
                    int(client_ip.replace('.', '')):
                client_ip = client['ip']
                client_data = client
        return client_data

    def get_client_data(self, cid):
        return self.cache.get(name=cid)


instance = RedisClient()
