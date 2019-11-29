# Util methods
class BaseSchemaClass(object):
    def __init__(self, classtype):
        self._type = classtype


def ClassFactory(name, argnames=None, BaseClass=BaseSchemaClass):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # here, the argnames variable is the one passed to the
            # ClassFactory call
            if key not in argnames:
                raise TypeError("Argument %s not valid for %s"
                    % (key, self.__class__.__name__))
            setattr(self, key, value)
        BaseClass.__init__(self, name[:-len("Class")])
    newclass = type(name, (BaseClass,),{"__init__": __init__})
    return newclass

def collect_attributes(cls):
    return [ attr for attr in cls.__dict__ if (not attr.startswith('__') and
                                               attr != 'schemaName' and
                                               attr != '_type' and
                                               attr != 'required')]


def convert_to_python_types(type_str):
    d={'string': str,
       'integer': int}
    return d.get(type_str, None)