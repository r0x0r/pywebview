"""Ownership for the Java-facing proxies pyjnius builds from PythonJavaClass.

pyjnius hands Java a *raw* pointer to the Python object. create_proxy_instance()
passes ``<long long><void *>py_obj`` into NativeInvocationHandler, and every
Java -> Python call casts that address straight back::

    py_obj = <object><void *>jptr

Nothing increfs it, and Java has no idea it is holding a pointer rather than a
reference. So if the Python object is collected while Java can still call it,
Java keeps a dangling pointer into freed heap, and the next callback invokes
whatever object has since been allocated at that address.

That is why this class of bug is so slippery: the symptom depends entirely on
what reoccupies the memory. It presents as a wrong result, or as "use of
deleted global reference" when the new occupant's JNI handle turns up where the
dead one's was expected, or as a plain SIGABRT, on whichever thread Java
happened to call back on. Nothing about it is deterministic, so a single clean
run proves nothing.

The rule is therefore absolute rather than best-effort: **a proxy must outlive
every call Java can still make on it.** Where the last possible call cannot be
established precisely, retain the proxy. Over-retaining costs bounded memory;
under-retaining aborts the process.
"""

from typing import Any

# Proxies that must not be collected for the remaining life of the process.
# Bounded in practice by the number of windows an app creates.
_owned: list[Any] = []


def retain(proxy: Any) -> Any:
    """Take permanent ownership of a Java-facing proxy.

    Use for any PythonJavaClass whose Java holder outlives, or may outlive, the
    Python object that created it - and for any whose last call from Java
    cannot be pinned down. Returns the proxy so it can be used inline.
    """
    if proxy is not None:
        _owned.append(proxy)

    return proxy
