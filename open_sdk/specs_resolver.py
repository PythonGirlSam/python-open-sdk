import copy
import yaml
import os
import logging
import urllib.parse as parse
from open_sdk import utils
from open_sdk import exceptions
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class Specs:
    def __init__(self, uri, service_name, service_version):
        self.service_name = '%s.yaml' % service_name.title()
        self.service_version = service_version
        self.operations = {}
        self.schemas = {}
        self.base_url = uri
        self.url = None
        self.data = None
        self.re_arrange()

    def read_specs(self):
        self.data = yaml.safe_load(open(os.path.abspath(
            os.path.join(os.path.dirname(__file__),os.path.join('specs',
                                                           os.path.join(
            self.service_version, self.service_name))))))

    def resolve_schema(self, schema, init=None):
        ret_schema = {}
        for schema_name, schema_structure in schema.items():
            if init:
                # schemaClass = ClassFactory(schema_name + "Schema")
                # schemaClass.name = schema_name
                ret_schema[schema_name] = self.create_schema_assign_properties(schema_name,
                                                                               schema_structure)
                continue

            if 'type' in schema_structure and schema_structure['type'] ==\
                    'object':
                # properties to schema
                return self.create_schema_assign_properties(schema_name,
                                                            schema)
            elif init and 'type' in schema_structure and schema_structure['type'] != 'object':
                # for schemas having single property
                setattr(ret_schema[schema_name], schema_name,
                        self.resolve_schema({
                    schema_name: schema_structure}))
            else:
                if 'type' in schema_structure and schema_structure['type'] == \
                        'array':
                    if "$ref" in schema_structure['items']:
                        property_path = schema_structure['items']['$ref'].split('/')[-1]
                        nested_schema = self.data['components']['schemas'][
                            property_path]
                        return [self.create_schema_assign_properties(
                            schema_name,nested_schema)]
                    else:
                        ret_schema[schema_name] = [self.resolve_schema({
                            schema_name: schema_structure['items']})]
                elif "$ref" not in schema_structure :
                    prop = Property(name=schema_name, **schema_structure)
                    return prop
                elif "$ref" in schema_structure:
                    # time to populate nested schema
                    property_path = schema_structure['$ref'].split('/')[-1]
                    nested_schema = self.data['components']['schemas'][property_path]
                    return self.create_schema_assign_properties(schema_name,
                                                                nested_schema)

        return ret_schema

    def create_schema_assign_properties(self, schema_name, schema):
        schemaClass = utils.ClassFactory(schema_name + "Schema")
        schemaObj = schemaClass()
        schemaObj.schemaName = schema_name
        log.info("Creating Schema", schema_name)
        properties = []
        if 'properties' in schema:
            properties = [self.resolve_schema({key: property}) for key, property in
                          schema['properties'].items()]
        elif 'type' in schema and schema['type'] != 'object':
            properties = [self.resolve_schema({schema_name: schema})]
        elif 'type' in schema and schema['type'] != 'object':
            properties = [self.resolve_schema({schema_name: schema})]
        for property in properties:
            if isinstance(property, list):
                if not isinstance(property[0], Property):
                    property_name = property[0].schemaName
                else:
                    property_name = property[0].name
            else:
                if not isinstance(property, Property):
                    property_name = property.schemaName
                else:
                    property_name = property.name
            setattr(schemaObj, property_name, property)
        return schemaObj

    def re_arrange(self):
        """
          example: {"volumes":{"showVolumes":{"action":"get",
                                            "summary"  :"",
                                            "description" :"",
                                            "parameters":{}
                                           },
                             "deleteVolumes":{},
                             "listVolumes":{}
                           }
                 } // end of specs
        """
        if not self.data:
            self.read_specs()
        # parse Schemas and keep things ready
        self.url = parse.urljoin(self.base_url,
                                 parse.urlparse(
                                     self.data['servers'][0]['url']).path)

        self.schemas = self.resolve_schema(self.data['components'][
                                               'schemas'], init=True)

        for path, data in self.data['paths'].items():
            operation = {}
            for action, operation_data in data.items():
                # make operation id as the key
                operation[operation_data["operationId"]] = operation_data
                operation[operation_data["operationId"]]["action"] = action
                operation[operation_data["operationId"]]["path"] = path
                self.operations[operation_data["operationId"]] = operation_data
                del operation_data["operationId"]
                path_param = []
                query_param = []
                if 'parameters' in operation_data:
                    for parameter in operation_data["parameters"]:
                        if parameter["in"] == "path":
                            del parameter['in']
                            pathparamObj = RequestPathParameter(**parameter)
                            path_param.append(pathparamObj)
                        elif parameter["in"] == "query":
                            del parameter['in']
                            queryparamObj = RequestQueryParameter(**parameter)
                            query_param.append(queryparamObj)
                    operation_data["parameters"] = {}
                    operation_data["parameters"]["path"] = path_param
                    operation_data["parameters"]["query"] = query_param
                else:
                    operation_data['parameters'] = {}

                if 'requestBody' in operation_data :
                    resolved_req_body = self.resolve_request_body(
                        operation_data['requestBody']['content'][
                            'application/json'][
                            "schema"])
                    operation_data['requestBody'] = \
                        APIRequestBody('application/json', resolved_req_body)
                else:
                    operation_data['requestBody'] = {}

    def resolve_request_body(self, schema, parent=None):
        properties = []
        for key, attr in schema.items():
            if isinstance(attr, dict):
                picked_schema = self.resolve_request_body(attr, parent=key)
                if parent == 'properties':
                    if (isinstance(picked_schema,list) and isinstance(
                        picked_schema[0], utils.BaseSchemaClass)) or isinstance(
                            picked_schema,Property):
                        if (isinstance(picked_schema,list) and isinstance(
                        picked_schema[0], utils.BaseSchemaClass)):
                            picked_schema = Property(name=key,type=picked_schema)
                        properties.append(picked_schema)
                    schema[key] = picked_schema
                elif parent == "items" and isinstance(
                            picked_schema[0], Property):
                    return picked_schema
                else:
                    if isinstance(picked_schema, list) and isinstance(
                            picked_schema[0], Property):
                        # create schema, assign list of properties into
                        # schema
                        schemaClass = utils.ClassFactory(name= parent if parent
                        else "NameLess" +"Schema")
                        schemaObj = schemaClass()
                        if 'required' in schema:
                            setattr(schemaObj, 'required', schema['required'])
                        for prop in picked_schema:
                            if isinstance(prop, Property) or isinstance(prop,
                                                                       list) :
                                setattr(schemaObj, prop.name, prop)
                        picked_schema = schemaObj

                        if "items" in schema:
                            picked_schema = [picked_schema, ]
                    return picked_schema
            else:
                # drill down till you get ref  or you get a property
                if key == "$ref":
                    attr = attr.split("/")[-1]
                    pick_schema = copy.deepcopy(self.schemas[attr])
                    if parent =="items":
                        pick_schema = [pick_schema, ]
                    return pick_schema
                if key == "type" and attr not in ("object", "array") and \
                        parent != "properties":
                    prop = Property(name=parent, **schema)
                    return prop
        if properties :
            return properties
        return schema


class Property:
    def __init__(self, name, type, format=None, example=None,
                 description=None, **kwargs):
        self.name = name
        self.type = type
        self.format = format
        self.example = example
        self.description = description
        for key, value in kwargs.items():
            setattr(self, key, value)
    def __str__(self):
        return "name: %s, type: %s, format: %s, example: %s" % (self.name,
                                                                self.type,
                                                                self.format,
                                                                self.example)

class RequestParameter(ABC):
    def __init__(self, **kwargs):
        for kwarg, value in kwargs.items():
            if kwarg == "schema":
                for x, y in value.items():
                    setattr(self, x, y)
            else:
                setattr(self, kwarg, value)
        super().__init__()

    @abstractmethod
    def validate(self):
        pass


class RequestQueryParameter(RequestParameter):
    def validate(self, input):
        if isinstance(input, dict):
            if self.name not in input:
                raise exceptions.InvalidParameter('Invalid Parameter passed,'
                                                  ' kindly refer help!')
            input = input[self.name]

            if utils.convert_to_python_types(self.type) != type(input):
                raise exceptions.InvalidParameter(
                    'Invalid Parameter passed,required %s got %s !' % (
                    self.type, type(input)))
        else:
            raise exceptions.InvalidParameter()


class RequestPathParameter(RequestParameter):
    def validate(self, input):
        if utils.convert_to_python_types(self.type) != type(input):
            raise exceptions.InvalidParameter(
                'Invalid Parameter passed, required %s got %s !' % (
                    self.type, type(input)))


class APIRequestBody():
    def __init__(self, format=None, schema=None,
                 description=None):
        self.format = format
        self.schema = schema
        self.description = description

    def checkPropertyType(self, prop, value):
        if utils.convert_to_python_types(prop.type) != type(
                value):
            raise exceptions.RequestError("Malformed RequestBody")

    def validate(self, body, validateagainst=None):
        if not validateagainst:
            validateagainst = self.schema
        missing = list(set(validateagainst.required) - set(body.keys()))
        if missing:
            raise exceptions.RequestError('Request Body missing required'
                                          'properties %s.' %
                                          ','.join(missing))
        for property in utils.collect_attributes(validateagainst):
            prop = getattr(validateagainst,property)
            if isinstance(prop, Property):
                if prop.name in body:
                    self.checkPropertyType(prop, body.get(prop.name))
            elif isinstance(prop, list):
                if prop.name in body:
                    if not isinstance(body.get(prop.name), list):
                        raise exceptions.RequestError("Malformed RequestBody")
                    for x in body.get(prop.name):
                        if isinstance(prop, Property):
                            self.checkPropertyType(prop, body.get(prop.name))
                        else:
                            self.validate(x, prop)
            else:
                self.validate(body, prop)

