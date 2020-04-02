import json
import logging
import re
from collections import defaultdict
from itertools import chain, product
from pprint import pformat

from tornado.web import Finish, HTTPError

from biothings.utils.common import dotdict
from biothings.web.api.es.query import BiothingSearchError
from biothings.web.api.helper import BaseAPIHandler, BadRequest


class BaseESRequestHandler(BaseAPIHandler):
    '''
    Parent class of all Elasticsearch-based Request handlers, subclass of `BaseHandler`_.
    Contains handling for Elasticsearch-specific query params (like ``fields``, ``size``, etc)
    '''
    name = 'api'
    out_format = 'json'
    kwarg_types = ('control', )
    kwarg_methods = ('get', 'post')

    def initialize(self, biothing_type=None):
        '''
        Request Level initialization.
        '''
        super(BaseESRequestHandler, self).initialize()
        self.biothing_type = biothing_type or self.web_settings.ES_DOC_TYPE

        # Configure Google Analytics

        action_key = f'GA_ACTION_{self.name.upper()}_{self.request.method}'
        if hasattr(self.web_settings, action_key):
            self.ga_event_object_ret['action'] = getattr(self.web_settings, action_key)
        else:
            self.ga_event_object_ret['action'] = self.request.method

        logging.debug("Google Analytics Base object: %s", self.ga_event_object_ret)

    def prepare(self):

        super().prepare()
        self.out_format = self.grouped_options.control.out_format or 'json'

    def write_error(self, status_code, **kwargs):

        reason = kwargs.pop('reason', self._reason)
        assert '\n' not in reason

        message = {
            "code": status_code,
            "success": False,
            "error": reason
        }
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            if isinstance(exception, BadRequest) and exception.kwargs:
                message.update(exception.kwargs)

        self.finish(message)

class ESRequestHandler(BaseESRequestHandler):
    '''
    Default Implementation of ES Query Pipelines
    '''
    kwarg_types = ('control', 'esqb', 'es', 'transform')
    kwarg_methods = ('get', 'post')

    def get_cleaned_options(self, options):
        """
        Clean up inherent logic between keyword arguments.
        For example, enforce mutual exclusion relationships.
        """

        ### ESQB Stage ###

        # facet_size only relevent for aggs
        if not options.esqb.aggs:
            options.esqb.pop('facet_size', None)

        ### ES Backend Stage ###

        # no sorting when scrolling
        if options.es.fetch_all:
            options.es.pop('sort', None)
            options.es.pop('size', None)

        # fields=all should return all fields
        if options.es._source is not None:
            if not options.es._source:
                options.es.pop('_source')
            elif 'all' in options.es._source:
                options.es._source = True

        ### Transform Stage ###

        options.transform.biothing_type = self.biothing_type

        # inject original query terms
        if self.request.method == 'POST':
            queries = options.esqb.ids or options.esqb.q
            options.transform.templates = (dict(query=q) for q in queries)
            options.transform.template_miss = dict(notfound=True)
            options.transform.template_hit = dict()

        logging.debug("Cleaned options:\n%s", pformat(options, width=150))
        return options

    async def get(self, *args, **kwargs):
        return await self.execute_pipeline(*args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self.execute_pipeline(*args, **kwargs)

    async def execute_pipeline(self, *args, **kwargs):

        options = self.get_cleaned_options(self.grouped_options)
        options = self.pre_query_builder_hook(options)

        ###################################################
        #                   Build query
        ###################################################

        _query = self.web_settings.query_builder.build(options.esqb)
        _query = self.pre_query_hook(options, _query)

        ###################################################
        #                   Execute query
        ###################################################

        res = await self.web_settings.query_backend.execute(
            _query, options.es, self.biothing_type)
        res = self.pre_transform_hook(options, res)

        ###################################################
        #                 Transform result
        ###################################################

        res = self.web_settings.query_transform.transform(
            res, options.transform)
        res = self.pre_finish_hook(options, res)

        self.finish(res)

    def pre_query_builder_hook(self, options):
        '''
        Override this in subclasses.
        At this stage, we have the cleaned user input available.
        Might be a good place to implement input based tracking.
        '''
        return options

    def pre_query_hook(self, options, query):
        '''
        Override this in subclasses.
        By default, return raw query, if requested.
        Might want to persist this behavior by calling super().
        '''
        if options.control.rawquery:
            raise Finish(query.to_dict())
        return query

    def pre_transform_hook(self, options, res):
        '''
        Override this in subclasses.
        By default, return query response, if requested.
        Might want to persist this behavior by calling super().
        '''
        if options.control.raw:
            raise Finish(res)
        return res

    def pre_finish_hook(self, options, res):
        '''
        Override this in subclasses.
        Could implement additional high-level result translation.
        '''
        return res
