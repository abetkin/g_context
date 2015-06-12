from functools import wraps
from itertools import islice
from contextlib import contextmanager
from collections import Mapping
from copy import copy

from .util import Missing, ExplicitNone, threadlocal
from ._signals import pre_signal, post_signal
# from .exceptions import Exit


# TODO property to handle "pending" object in context
#
def ContextAttr(name, default=Missing):

    def fget(self):
        dic = self.__dict__.setdefault('_contextattrs', {})
        context = get_context()
        if name in dic:
            return dic[name]
        if default is not Missing:
            return context.get(name, default)
        try:
            return context[name]
        except KeyError:
            raise AttributeError(name)

    def fset(self, value):
        dic = self.__dict__.setdefault('_contextattrs', {})
        dic[name] = value

    return property(fget, fset)





@contextmanager
def add_context(obj):
    context = get_context()
    pushed = context.push(obj)
    try:
        yield
    except Exception as ex:
        ex.gctx = copy(context)
        raise ex
    finally:
        if pushed: context.pop()


# context: stack -> dict, ChainMap ?

@Mapping.register
class ObjectsStack:
    def __init__(self, objects=None):
        self._objects = objects or []

    @property
    def objects(self):
        return self._objects

    def __copy__(self):
        return self.__class__(self.objects)

    def __repr__(self):
        return repr(self.objects)

    def __getitem__(self, key):
        if isinstance(key, int):
            # a bit of user-friendly interface
            return self.objects[key]
        for obj in self.objects:
            try:
                if isinstance(obj, Mapping):
                    return obj[key]
                return getattr(obj, key)
            except (KeyError, AttributeError):
                pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def __bool__(self):
        return bool(self.objects)

    def get(self, key, default=None):
        return self[key] if key in self else default

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            pass

    def __iter__(self):
        yield from self.objects

    def __len__(self):
        return len(self.objects)

    def __eq__(self, other):
        if isinstance(other, ObjectsStack):
            return self.objects == other.objects

    def __ne__(self, other):
        return not (self == other)

    def push(self, obj):
        if obj is not None and obj not in self._objects:
            self._objects.insert(0, obj)
            return True

    def pop(self):
        self._objects.pop(0)



def get_context(obj=None):
    # Usually to be called from objects as properties
    #
    context = threadlocal().setdefault('context', ObjectsStack())
    if obj is not None and obj is context.objects[-1]:
        tple = tuple(islice(context.objects, 1, None))
        return ObjectsStack(tple)
    return copy(context)



from blinker import signal




class GrabContextWrapper:

    def __init__(self, get_context_object):
        self.get_context_object = get_context_object

    def as_manager(self, *run_args, **run_kwargs):
        instance = self.get_context_object(*run_args, **run_kwargs)
        return add_context(instance)

    
    def __call__(self, func):

    
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.as_manager(*args, **kwargs):
                # TODO try..except
                pre_exec.send(args=args, kwargs=kwargs)
                ret = func(*args, **kwargs)
                post_exec.send(args=args, kwargs=kwargs)
                return ret

        pre_exec = pre_signal(wrapper)
        post_exec = post_signal(wrapper)

        return wrapper


# define pre-post hooks with generator

@GrabContextWrapper
def function(*args, **kwargs):
    return None

@GrabContextWrapper
def method(*args, **kwargs):
    return args[0]
