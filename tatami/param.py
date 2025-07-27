from typing import Optional


class Header:
    """Marks a parameter as a header parameter.
    
    Args:
        name: The name of the header. If not provided, defaults to the parameter name.
              Underscores will be converted to hyphens and the name will be title-cased.
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name

class Query:
    """Marks a parameter as a query parameter.
    
    Args:
        name: The name of the query parameter. If not provided, defaults to the parameter name.
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name

class Path:
    """Marks a parameter as a path parameter.
    
    Args:
        name: The name of the path parameter. If not provided, defaults to the parameter name.
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name

