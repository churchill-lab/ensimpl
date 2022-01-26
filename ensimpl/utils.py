"""Useful generic utilities for the package.
"""
from collections import OrderedDict
from functools import cmp_to_key
from operator import itemgetter as ig
from typing import Any
from typing import AnyStr
from typing import Dict
from typing import List
from typing import Optional
from typing import OrderedDict as OrderedDictTyping
from urllib.request import urlopen

import bz2
import gzip
import logging
import os
import random
import re
import sqlite3
import string

REGEX_ENSEMBL_MOUSE_ID = re.compile('ENSMUS([EGTP])[0-9]{11}', re.IGNORECASE)
REGEX_ENSEMBL_HUMAN_ID = re.compile('ENS([EGTP])[0-9]{11}', re.IGNORECASE)
REGEX_MGI_ID = re.compile('MGI:[0-9]{1,}', re.IGNORECASE)
REGEX_REGION = re.compile('(CHR|)*\s*([0-9]{1,2}|X|Y|MT)\s*(-|:)?\s*(\d+\.*\d*)\s*(MB|M|K|)?\s*(-|:|)?\s*(\d+\.*\d*|)\s*(MB|M|K|)?', re.IGNORECASE)

logging.basicConfig(format='[Ensimpl] [%(asctime)s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')


def get_logger() -> logging.Logger:
    """Get the logger.

    Returns:
        logging.Logger: The logging object.
    """
    return logging.getLogger(__name__)


def configure_logging(level: Optional[int] = 0) -> None:
    """Configure the logger with the specified `level`. Valid `level` values
    are:

    ======  =================================
    level   logging value
    ======  =================================
    0       logging.WARNING is informational
    1       logging.INFO is user debug
    2+      logging.DEBUG is developer debug
    ======  =================================

    Anything greater than 2 is treated as 2.

    Args:
        The logging level; defaults to 0.
    """
    if level == 0:
        get_logger().setLevel(logging.WARN)
    elif level == 1:
        get_logger().setLevel(logging.INFO)
    elif level > 1:
        get_logger().setLevel(logging.DEBUG)


def dictify_row(cursor: sqlite3.Cursor, row: sqlite3.Row) -> OrderedDictTyping:
    """Turns the given row into a dict where the keys are the column names.

    Args:
        cursor (sqlite3.Cursor): The database cursor.
        row (sqlite3.Row): The current row.

    Returns:
        An OrderedDict where keys are column names.
    """
    d = OrderedDict()
    for i, col in enumerate(cursor.description):
        d[col[0]] = row[i]
    return d


def dictify_cursor(cursor: sqlite3.Cursor) -> List[OrderedDictTyping]:
    """All rows are converted into a :class:`collections.OrderedDict` where
    keys are the column names.

    Args:
        cursor (sqlite3.Cursor): The database cursor.

    Returns:
        A list of dicts where keys are column names.

    """
    return [dictify_row(cursor, row) for row in cursor]


def cmp(value_1: Any, value_2: Any) -> int:
    """Compare two values.  The return value will be ``-1`` if
    `value_1` is less than `value_2`, ``0`` if `value_1` is equal
    to `value_2`, or ``1`` if `value_1` is greater than `value_2`.

    Args:
        value_1: The first value.
        value_2: The second value.

    Returns:
        int:  -1, 0, 1
    """
    return (value_1 > value_2) - (value_1 < value_2)


def create_random_string(size: Optional[int] = 6,
                         chars: List[str] = string.ascii_uppercase + string.digits) -> str:
    """Generate a random string of length `size` using the characters
    specified by `chars`.

    Args:
        size: The length of the string.  6 is the default.
        chars: The characters to use.

    Returns:
        str: A random generated string.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def delete_file(file_name: str) -> None:
    """ Delete specified `file_name`.  This will fail silently.

    Args:
        file_name: The name of file to delete.
    """
    try:
        os.remove(file_name)
    except OSError as ose:
        pass


def format_time(start: float, end: float) -> str:
    """Format length of time between start and end into a readable string.

    Args:
        start: The start time.
        end: The end time.

    Returns:
        A formatted string of hours, minutes, and seconds.
    """
    hours, rem = divmod(end-start, 3600)
    minutes, seconds = divmod(rem, 60)
    return f'{int(hours):0>2}:{int(minutes):0>2}:{int(seconds):05.2f}'


def get_file_name(url: str, directory: Optional[str] = None) -> AnyStr:
    """Get the file name of `url`.  If `directory` has a value, return the
    name of the file with directory prepended.

    Examples:
        >>> get_file_name('http://www.google.com/a/b/c/file.html', '/tmp')
        '/tmp/file.html

    Args:
        url: The url of a file.
        directory: The name of a directory.

    Returns:
        The full path of file.
    """
    download_file_name = url.split('/')[-1]
    local_directory = directory if directory else os.getcwd()
    return os.path.abspath(os.path.join(local_directory, download_file_name))


def is_url(url: str) -> bool:
    """Check if this is a URL or not by just checking the protocol.

    Args:
        url: A string in the form of a url.

    Returns:
        True if `url` has a valid protocol, False otherwise.
    """
    if url and url.startswith(('http://', 'https://', 'ftp://')):
        return True

    return False


def merge_two_dicts(x: dict, y: dict) -> Dict:
    """Given two dicts, merge them into a new dict as a shallow copy.

    Args:
        x: Dictionary 1.
        y: Dictionary 2.

    Returns:
        The merged dictionary.
    """
    z = x.copy()
    z.update(y)
    return z


def multikeysort(items: List[Dict], columns: List[str]) -> List[Dict]:
    """Sort a ``list`` of ``dicts`` by multiple keys in ascending or descending
    order. To sort in descending order, prepend a '-' (minus sign) on the
    column name.

    Pulled from: https://stackoverflow.com/questions/1143671/python-sorting-list-of-dictionaries-by-multiple-keys

    Examples:
        >>> my_list = [
            {'name': 'apple', 'count': 10, 'price': 1.00},
            {'name': 'banana', 'count': 5, 'price': 1.00},
            {'name': 'orange', 'count': 20, 'price': 2.00},
        ]

        >>> multikeysort(my_list, ['-name', 'count'])
        [{'count': 20, 'name': 'orange', 'price': 2.0},
         {'count': 5, 'name': 'banana', 'price': 1.0},
         {'count': 10, 'name': 'apple', 'price': 1.0}]

        >>> multikeysort(my_list, ['-price', 'count'])
        [{'count': 20, 'name': 'orange', 'price': 2.0},
         {'count': 5, 'name': 'banana', 'price': 1.0},
         {'count': 10, 'name': 'apple', 'price': 1.0}]

    Args:
        items (list): The ``list`` of ``dict`` objects.
        columns (list): A ``list`` of columns names to sort `items`.

    Returns:
        list: The sorted ``list``.

    """
    comparers = [
        ((ig(col[1:].strip()), -1) if col.startswith('-') else (
        ig(col.strip()), 1))
        for col in columns
    ]

    def comparer(left, right):
        comparer_iter = (
            cmp(fn(left), fn(right)) * mult
            for fn, mult in comparers
        )
        return next((result for result in comparer_iter if result), 0)

    return sorted(items, key=cmp_to_key(comparer))


def open_resource(resource: str, mode: Optional[str] = 'rb'):
    """Open different types of files and return a handle to that resource.
    Valid types of resources are gzipped and bzipped files along with URLs.

    Args:
        resource: A string representing a file or url.
        mode: Mode to open the file.

    Returns:
        A handle to the opened resource.
    """
    if not resource:
        return None

    if not isinstance(resource, str):
        return resource

    if resource.endswith(('.gz', '.Z', '.z')):
        return gzip.open(resource, mode)
    elif resource.endswith(('.bz', '.bz2', '.bzip2')):
        return bz2.BZ2File(resource, mode)
    elif resource.startswith(('http://', 'https://', 'ftp://')):
        return urlopen(resource)
    else:
        return open(resource, mode)


def str2bool(val: str) -> bool:
    """Convert a string into a boolean.  Valid strings that return ``True``
    are: ``true``, ``1``, ``t``, ``y``, ``yes``

    Canse-sensitivity does NOT matter.  ``yes`` is the same as ``YeS``.

    Args:
        val: A string representing the boolean value of ``True``.

    Returns:
        True val represents a boolean True
    """
    return str(val).lower() in ['true', '1', 't', 'y', 'yes']


class Region:
    """Encapsulates a genomic region.

    Attributes:
        chromosome (str): The chromosome name.
        start_position (int): The start position.
        end_position (int): The end position.
    """
    def __init__(self):
        """Initialization."""
        self.chromosome: str
        self.start_position: int
        self.end_position: int

    def __str__(self):
        """Return string representing this region.

        Returns:
            str: In the format of chromosome:start_position-end_position.
        """
        return f'{self.chromosome}:{self.start_position}-{self.end_position}'

    def __repr__(self):
        """Internal representation.

        Returns:
            str: The keys being the attributes.
        """
        return (f'{self.__class__}({self.chromosome}:'
                f'{self.start_position}-{self.end_position})')


def nvl(value: Any, default: Any) -> Any:
    """Returns `value` if value has a value, else `default`.

    Args:
        value: The value to evaluate.
        default: The default value.

    Returns:
        Either `value` or `default`.
    """
    return value if value else default


def nvli(value, default) -> int:
    """Returns `value` as an int if `value` can be converted, else `default`.

    Args:
        value: The value to evaluate and convert to an it.
        default: The default value.

    Returns:
        Either `value` or `default`.
    """
    ret = default
    if value:
        try:
            ret = int(value)
        except ValueError:
            pass
    return ret


def get_multiplier(factor: str) -> int:
    """Get multiplying factor.

    The factor value should be 'mb', 'm', or 'k' and the correct multiplier
    will be returned.

    Args:
        factor: One of 'mb', 'm', or 'k'.

    Returns:
        The multiplying value.
    """
    if factor:
        factor = factor.lower()

        if factor == 'mb':
            return 1000000
        elif factor == 'kb':
            return 1000

    return 1


def str_to_region(location: str) -> Region:
    """Parse a string into a genomic location.

    Args:
        location: The genomic location (range).

    Returns:
        A Region object.

    Raises:
        ValueError: If `location` is invalid.
    """
    if not location:
        raise ValueError('No location specified')

    valid_location = location.strip()

    if ('-' not in valid_location) and (' ' not in valid_location) and \
            (':' not in valid_location):
        raise ValueError('Incorrect location format')

    if len(valid_location) <= 0:
        raise ValueError('Empty location')

    match = REGEX_REGION.match(valid_location)

    if not match:
        raise ValueError('Invalid location string')

    loc = Region()
    loc.chromosome = match.group(2)
    loc.start_position = match.group(4)
    loc.end_position = match.group(7)
    multiplier_one = match.group(5)
    multiplier_two = match.group(8)

    if '.' in loc.start_position:
        loc.start_position = float(loc.start_position)
    else:
        loc.start_position = int(loc.start_position)

    if '.' in loc.end_position:
        loc.end_position = float(loc.end_position)
    else:
        loc.end_position = int(loc.end_position)

    if multiplier_one:
        loc.start_position *= get_multiplier(multiplier_one)

    if multiplier_two:
        loc.end_position *= get_multiplier(multiplier_two)

    return loc


def is_valid_region(term: str) -> bool:
    """Check if a string can be parsed into a genomic location.

    Args:
        term: The genomic location (range).

    Returns:
        True if valid region, False otherwise
    """
    try:
        if ('-' not in term) and (' ' not in term) and (':' not in term):
            raise ValueError('not correct format')

        region = str_to_region(term)

        if region.chromosome is None or \
                region.start_position is None or \
                region.end_position is None:
            return False

    except ValueError as ve:
        return False

    return True


def validate_ensembl_id(ensembl_id: str) -> str:
    """Validate an id to make sure it conforms to the convention.

    Args:
        ensembl_id: The Ensembl identifer to test.

    Returns:
        The Ensembl id.

    Raises:
        ValueError: If `ensembl_id` is invalid.
    """
    if not ensembl_id:
        raise ValueError('No Ensembl ID')

    valid_id = ensembl_id.strip()

    if len(valid_id) <= 0:
        raise ValueError('Empty Ensembl ID')

    if REGEX_ENSEMBL_HUMAN_ID.match(valid_id):
        return valid_id
    elif REGEX_ENSEMBL_MOUSE_ID.match(valid_id):
        return valid_id

    raise ValueError(f'Invalid Ensembl ID: {ensembl_id}')


