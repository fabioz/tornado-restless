#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""

"""
from datetime import datetime
import logging
from threading import Thread
from urllib.parse import urljoin
import os

import requests
from sqlalchemy import create_engine, schema, Column, Integer, String, ForeignKey, DateTime, func, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship, scoped_session, backref
import tornado.web
import tornado.ioloop

from tornado_restless import ApiManager as TornadoRestlessManager
import sys
import pytest
import asyncio
import threading

__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '21.08.13'

import socket


def get_free_port():
    '''
    Helper to get free port (usually not needed as the server can receive '0' to connect to a new
    port).
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    _, port = s.getsockname()
    s.close()
    return port


class TestBase(object):
    """
        Base class for all tests

        sets up tornado_restless and flask_restless
    """

    config = {
        'dns': 'sqlite:///:memory:',
        'encoding': 'utf-8',
    }

    @pytest.fixture(autouse=True)
    def set_up(self):
        if sys.platform == 'win32':
            # See issues:
            # https://github.com/tornadoweb/tornado/issues/2608
            # https://bugs.python.org/issue37373
            if sys.version_info[:3] != (3, 8, 1):
                raise AssertionError('Check if this is still needed.')
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        event = threading.Event()

        class TornadoThread(Thread):

            def run(s):  # @NoSelf
                try:
                    self._set_up_alchemy()
                    self._set_up_models()

                    asyncio.set_event_loop(asyncio.new_event_loop())

                    app = tornado.web.Application([])
                    self.port = get_free_port()
                    app.listen(self.port)
                    self.tornado = app
                    self.io_loop = tornado.ioloop.IOLoop.instance()

                    Session = self.alchemy['Session']

                    self.api = {'tornado': TornadoRestlessManager(application=self.tornado, session_maker=Session)}

                    for model, methods in self.models.values():
                        if methods == "all":
                            self.api['tornado'].create_api(model, methods=TornadoRestlessManager.METHODS_ALL)
                        else:
                            self.api['tornado'].create_api(model)
                finally:
                    event.set()

                self.io_loop.start()
                self.tear_down_alchemy()

        self.threads = {'tornado': TornadoThread(target=self, name='TornadoThread')}
        self.threads['tornado'].start()
        event.wait()

    @pytest.fixture(autouse=True)
    def tear_down(self):
        yield
        self.tear_down_tornado()

    def curl_tornado(self, url, method='get', assert_for=200, **kwargs):
        url = urljoin('http://localhost:%u' % self.port, url)
        r = getattr(requests, method)(url, **kwargs)
        if assert_for == 200:
            r.raise_for_status()
        else:
            assert assert_for == r.status_code
        try:
            try:
                return r.json()
            except ValueError:
                return None
        finally:
            r.close()

    def _set_up_alchemy(self):
        """
            Init SQLAlchemy engine
        """
        engine = create_engine(self.config['dns'])
        metadata = schema.MetaData()
        Session = scoped_session(sessionmaker(bind=engine))
        Base = declarative_base(metadata=metadata)

        self.alchemy = {'Base': Base, 'Session': Session, 'engine': engine}

    def tear_down_alchemy(self):
        Base = self.alchemy['Base']
        engine = self.alchemy['engine']

        Base.metadata.drop_all(engine)
        engine.dispose()

        del self.alchemy

    def _set_up_models(self):
        """
            Create models
        """

        Base = self.alchemy['Base']
        Session = self.alchemy['Session']
        engine = self.alchemy['engine']

        class City(Base):
            __tablename__ = "cities"

            _plz = Column(String(6), primary_key=True)

            name = Column(String, unique=True)

        class Person(Base):
            __tablename__ = 'persons'

            _id = Column(Integer, primary_key=True)
            name = Column(String, unique=True)
            birth = Column(DateTime)

            @hybrid_property
            def age(self):
                return (datetime.now() - self.birth).days / 365.25

            @age.expression
            def age(self):
                return func.now() - self.birth

            def __init__(self, name, age):
                self.name = name
                self.birth = datetime.now().replace(year=datetime.now().year - age)

        class City2Person(Base):
            __tablename__ = 'city2persons'

            _city = Column(ForeignKey(City._plz), primary_key=True)
            city = relationship(City, lazy="joined", backref=backref('persons', lazy="dynamic"))

            _user = Column(ForeignKey(Person._id), primary_key=True)
            user = relationship(Person, lazy="joined", backref=backref('cities', lazy="dynamic"))

            def __init__(self, city, user):
                self._city = city._plz
                self._user = user._id

        class Computer(Base):
            __tablename__ = 'computers'

            _id = Column(Integer, primary_key=True)

            cpu = Column(Float)
            ram = Column(Float)

            _user = Column(ForeignKey(Person._id))
            user = relationship(Person, backref='computers')

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        self.models = {'Person': (Person, "all"), 'Computer': (Computer, "all"), 'City': (City, "read")}

        frankfurt = City(_plz=60400, name="Frankfurt")
        berlin = City(_plz=10800, name="Berlin")

        self.citites = [frankfurt, berlin]

        anastacia = Person('Anastacia', 44)
        bernd = Person('Bernd', 48)
        claudia = Person('Claudia', 20)
        dennise = Person('Dennise', 14)
        emil = Person('Emil', 81)
        feris = Person('Feris', 10)

        self.persons = {p.name: p for p in [anastacia, bernd, claudia, dennise, emil, feris]}

        a1 = Computer(user=anastacia, cpu=3.2, ram=4)
        a2 = Computer(user=anastacia, cpu=12, ram=4)
        b1 = Computer(user=bernd, cpu=12, ram=8)
        e1 = Computer(user=emil, cpu=1.6, ram=2)
        e2 = Computer(user=emil, cpu=3.4, ram=4)

        self.computers = [a1, a2, b1, e1, e2]

        session = Session()
        session.add_all(self.citites)
        session.add_all(self.persons.values())
        session.add_all(self.computers)
        session.commit()

        session.refresh(bernd)
        session.refresh(anastacia)
        self.assocs = [City2Person(frankfurt, bernd), City2Person(frankfurt, anastacia), City2Person(berlin, bernd)]
        session.add_all(self.assocs)
        session.commit()

    def tear_down_tornado(self):

        def stop():
            """
                Stop the IOLoop
            """
            self.io_loop.stop()

        self.io_loop.add_callback(stop)
        self.threads['tornado'].join()
