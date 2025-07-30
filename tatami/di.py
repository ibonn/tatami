import inspect
from dataclasses import dataclass
from enum import Enum
from functools import partial, wraps
from typing import (Annotated, Any, Callable, Optional, TypeVar, Union,
                    get_args, get_origin, overload)


class Scope(Enum):
    SINGLETON = 'singleton'
    REQUEST = 'request'

T = TypeVar('T')

@dataclass
class InjectableMetadata:
    scope: Scope
    singleton: Optional[T] = None

Injectable = TypeVar('Injectable', bound=InjectableMetadata)

class TatamiInternals:
    # Funny little reference to React
    __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: Injectable

ClassWithInternals = TypeVar('ClassWithInternals', bound=TatamiInternals)

__TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = '__TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED'


class Inject:
    def __init__(self, factory: Optional[Callable] = None, scope: Scope = Scope.SINGLETON):
        if factory is not None:
            factory = inject(factory)
        
        self.scope = scope
        self.factory = factory

@overload
def injectable(cls: type[T]) -> T:
    ...

@overload
def injectable(scope: Scope = Scope.SINGLETON) -> type:
    ...

@overload
def injectable(*, scope: Scope = Scope.SINGLETON) -> type:
    ...

def injectable(scope_or_cls: Optional[Union[Scope, type]] = None, scope: Scope = Scope.SINGLETON) -> type:
    def decorator(cls: ClassWithInternals, scope: Scope = Scope.SINGLETON) -> ClassWithInternals:
        # Add metadata to the class
        cls.__TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = InjectableMetadata(scope=scope)
        
        # Inject into its __init__ method
        cls.__init__ = inject(cls.__init__)

        return cls
    
    # @injectable (no parentheses, no arguments)
    if isinstance(scope_or_cls, type):
        return decorator(scope_or_cls)
    
    # @injectable() or @injectable(Scope.SINGLETON)
    scope = scope_or_cls if isinstance(scope_or_cls, Scope) else scope
    return partial(decorator, scope=scope)


def is_tatami_object(cls: type) -> bool:
    return hasattr(cls, __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED)

def get_tatami_metadata(cls: type):
    return getattr(cls, __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED)

def is_injectable(cls: type) -> bool:
    return (
            is_tatami_object(cls) and isinstance(getattr(cls, __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED), InjectableMetadata)  # For decorated injectables
        ) or (
            get_origin(cls) is Annotated and isinstance(get_args(cls)[1], Inject)   # For explicitly annotated injectables -> Annotated[T, Inject()]
        )

def _inject_object_instance(t: type):
    metadata: InjectableMetadata = getattr(t, __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED)
    if metadata.scope == Scope.SINGLETON:
        if metadata.singleton is None:
            metadata.singleton = t()
        return metadata.singleton
    
    return t()

def _inject_instance_depending_on_scope(name: str, type_ :type, scope: Scope, injected: dict[str, Any], non_singletons: dict[str, Callable]):
    if scope == Scope.SINGLETON:
        injected[name] = _inject_object_instance(type_)
    else:
        non_singletons[name] = lambda t=type_: _inject_object_instance(t)
    

def inject(fn: Callable) -> Callable:
    signature = inspect.signature(fn)

    injected = {}
    non_singletons = {}

    for parameter in signature.parameters.values():
        if is_injectable(parameter.annotation):
            if is_tatami_object(parameter.annotation):
                metadata = get_tatami_metadata(parameter.annotation)
                _inject_instance_depending_on_scope(parameter.name, parameter.annotation, metadata.scope, injected, non_singletons)
            else:

                target_type, inject_object = get_args(parameter.annotation)

                if inject_object.factory is None:
                    # Try injecting the type, it might be an injectable class (same as above) but explicitly declared
                    if is_injectable(target_type):
                        _inject_instance_depending_on_scope(parameter.name, target_type, target_type.scope, injected, non_singletons)
                    # If it is not, raise an exception
                    else:
                        raise TypeError(f'Cannot inject object of type {target_type}')
                else:
                    # Here singletons are injected only
                    if inject_object.scope == Scope.SINGLETON:
                        injected[parameter.name] = inject_object.factory()
                    else:
                        non_singletons[parameter.name] = inject_object.factory
            

    def injected_fn(*args, **kwargs):
        for name, factory in non_singletons.items():
            injected[name] = factory()
        return fn(*args, **{**kwargs, **injected})
        
    return wraps(fn)(injected_fn)