"""
CodeTrace AI — Error Classifier

Maps Python exception types to their dedicated analyzer.
Returns an "unknown" analyzer for unsupported exceptions.
"""

from .analyzers.index_error import IndexErrorAnalyzer
from .analyzers.key_error import KeyErrorAnalyzer
from .analyzers.name_error import NameErrorAnalyzer
from .analyzers.type_error import TypeErrorAnalyzer
from .analyzers.zero_division import ZeroDivisionErrorAnalyzer


# Registry: exception type name → analyzer class
ANALYZER_REGISTRY: dict[str, type] = {
    "IndexError": IndexErrorAnalyzer,
    "ZeroDivisionError": ZeroDivisionErrorAnalyzer,
    "KeyError": KeyErrorAnalyzer,
    "NameError": NameErrorAnalyzer,
    "TypeError": TypeErrorAnalyzer,
}


def get_analyzer(exception_type: str):
    """
    Return the appropriate analyzer for a given exception type.

    Returns a GenericAnalyzer for unsupported types.
    """
    analyzer_cls = ANALYZER_REGISTRY.get(exception_type)
    if analyzer_cls:
        return analyzer_cls()
    from .analyzer import GenericAnalyzer
    return GenericAnalyzer()
