import re
import requests
import json
import logging
from oslo_config import cfg

from open_sdk import config_loader
from open_sdk.specs_resolver import Specs
from open_sdk import exceptions

CONF = cfg.CONF
config_loader.register_conf_file()
log = logging.getLogger(__name__)


class Client:
    def __init__(self, service_name, x_auth_token):
        log.info("Init Client")
        self.service_name = service_name
        self.service_version = getattr(CONF.api_versions, service_name
                                       + '_api_version')
        self.service_specs = Specs(CONF.api_uri,
                                   self.service_name,
                                   self.service_version)
        # once specs reading is successful assign dynamic attributes
        for operation_name, operation_attr in \
                self.service_specs.operations.items():
            operatorObj = Operation(baseurl=self.service_specs.url,
                                    in_path_params= operation_attr[
                                        'parameters'].get('path',None),
                                    query_path_params= operation_attr[
                                        'parameters'].get('query',None),
                                    path=operation_attr['path'],
                                    requestbody=operation_attr['requestBody'],
                                    responses=operation_attr['responses'],
                                    action=operation_attr['action'],
                                    x_auth_token=x_auth_token
                                    )
            setattr(self, operation_name, operatorObj)


class Operation:
    def __init__(self, baseurl=None, x_auth_token=None, **kwargs):
        self.in_path_params = kwargs['in_path_params']
        self.query_path_params = kwargs['query_path_params']
        self.responses = kwargs['responses']
        self.result = None
        self.result_code = None
        self.__baseurl = baseurl
        self.__url = baseurl
        self.__x_auth_token = x_auth_token
        self.__timeout = None
        self.__params = None
        self.__path = kwargs['path']
        self.__action = kwargs['action']
        self.__requestBody = kwargs['requestbody']
        self.__body = None


    def reset(self):
        self.__url = self.__baseurl
        self.__timeout = None
        self.__params = None
        self.__body = None

    def form_url(self, *args, **kwargs):
        # Fetch path parameters
        path_params = []
        values = []
        if self.in_path_params:
            if args:
                if len(args) != len(self.in_path_params):
                    raise exceptions.InvalidParameter("Required Number of path parameters are not passed!")
                if args:
                    for index, value in enumerate(args):
                        self.in_path_params[index].validate(input=value)
            else:
                raise exceptions.InvalidParameter("This request expects path "
                                                  "parameters.")
            values = args

            expression = '(\{.*?\})'
            url = re.sub(expression,'%s', self.__path)
            url = url % values
            self.__url = self.__url + url
        else:
            self.__url = self.__url + self.__path

    def __call__(self, *args, **kwargs):
        self.reset()
        return self.request(*args, **kwargs)

    def execute_request(self):
        pass

    @property
    def header(self):
        return self.__header

    def __prepareheader(self):
        self.__headers = {}
        if self.__body:
            self.__headers['Content-Type'] = 'application/json'

        if self.responses:
            # we accept a response Body back
            self.__headers['Accept'] = 'application/json'

        if self.__x_auth_token:
            self.__headers['x-auth-token'] = self.__x_auth_token

    def request(self, *args, **kwargs):
        self.form_url(*args)
        if self.__requestBody:
            if 'body' not in kwargs:
                raise exceptions.RequestError('Request missing request body.')
            self.__body = kwargs['body']
            self.__requestBody.validate(self.__body)

        if self.query_path_params:
            if 'params' in kwargs:
                for req_query_param_obj in self.query_path_params:
                    req_query_param_obj.validate(kwargs['params'])
                self.__params = kwargs['params']

        if not hasattr(self, '__verify_cert'):
            self.__verify_cert = None

        if not hasattr(self, '__headers'):
            self.__prepareheader()

        log.info("Hitting URL %s:%s" %(self.__action, self.__url))
        resp = requests.request(
            method=self.__action,
            url=self.__url,
            verify=self.__verify_cert,
            json=self.__body,
            timeout=self.__timeout,
            params=self.__params,
            headers=self.__headers)

        body = None
        if resp.text:
            try:
                body = json.loads(resp.text)
            except ValueError as e:
                log.error("Load http response text error: %s", e)

        if resp.status_code >= 400:
            raise exceptions.RequestError(resp, body)

        self.result = Result(body, resp.status_code)
        return self.result


class Result:
    def __init__(self, result, result_code):
        self.result = result
        self.result_code = result_code
        # check number of keys
        self.keys_len = len(self.result)
        self.value_len = len(self.result.values())
        self.value_iter = None
        if self.keys_len == 1:
            for value in self.result.values():
                if isinstance(value, list):
                    self.value_iter = iter(value)
                    break
            if not self.value_iter:
                self.value_iter = iter(self.result.values())

    def __str__(self):
        return "Request Response : %s" % str(self.result_code)

    def list_n(self, n=0):
        ret_value = []
        if self.value_iter:
            for iter_num in range(n):
                try:
                    ret_value.append(next(self.value_iter))
                except StopIteration:
                    pass
        else:
            return self.result
        return ret_value

    def list_all(self):
        if self.keys_len == 1:
            return self.value_iter
        else:
            return self.result

    def get(self):
        try:
            if self.value_iter:
                return next(self.value_iter)
            else:
                return self.result
        except StopIteration:
            log.info("End of result list reached.")

c1 = Client('pets',x_auth_token="vgdSLA46VYHupndwmI-wFc7_9PHLtyqa7ea1ok_QGiFV2cO49G6DH7gGV5ZCDqg2BPeuVupOQP90ZQQlxCh3ozzxSPc1IntWF9Koxqz9QH-h-35obYIdycLkzsdx2DJrifDFZf5YYdENJwef7s1EwhBtwCvsROm6UwuNcu7kGgQ" )
c1.createPets()