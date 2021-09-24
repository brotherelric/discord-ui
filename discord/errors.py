"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING, Any, Tuple, Union

if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientWebSocketResponse

    try:
        from requests import Response

        _ResponseType = Union[ClientResponse, Response]
    except ModuleNotFoundError:
        _ResponseType = ClientResponse

    from .interactions import Interaction

__all__ = (
    'DiscordException',
    'ClientException',
    'NoMoreItems',
    'GatewayNotFound',
    'HTTPException',
    'Forbidden',
    'NotFound',
    'DiscordServerError',
    'InvalidData',
    'InvalidArgument',
    'LoginFailure',
    'ConnectionClosed',
    'PrivilegedIntentsRequired',
    'InvalidLength',
    'OutOfValidRange',
    'WrongType',
    'InvalidEvent',
    'MissingListenedComponentParameters',
    'CouldNotParse',
)


class DiscordException(Exception):
    """Base exception class for discord.py

    Ideally speaking, this could be caught to handle any exceptions raised from this library.
    """

    pass


class ClientException(DiscordException):
    """Exception that's raised when an operation in the :class:`Client` fails.

    These are usually for exceptions that happened due to user input.
    """

    pass


class NoMoreItems(DiscordException):
    """Exception that is raised when an async iteration operation has no more items."""

    pass


class GatewayNotFound(DiscordException):
    """An exception that is raised when the gateway for Discord could not be found"""

    def __init__(self):
        message = 'The gateway to connect to discord was not found.'
        super().__init__(message)


def _flatten_error_dict(d: Dict[str, Any], key: str = '') -> Dict[str, str]:
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        new_key = key + '.' + k if key else k

        if isinstance(v, dict):
            try:
                _errors: List[Dict[str, Any]] = v['_errors']
            except KeyError:
                items.extend(_flatten_error_dict(v, new_key).items())
            else:
                items.append((new_key, ' '.join(x.get('message', '') for x in _errors)))
        else:
            items.append((new_key, v))

    return dict(items)


class HTTPException(DiscordException):
    """Exception that's raised when an HTTP request operation fails.

    Attributes
    ------------
    response: :class:`aiohttp.ClientResponse`
        The response of the failed HTTP request. This is an
        instance of :class:`aiohttp.ClientResponse`. In some cases
        this could also be a :class:`requests.Response`.

    text: :class:`str`
        The text of the error. Could be an empty string.
    status: :class:`int`
        The status code of the HTTP request.
    code: :class:`int`
        The Discord specific error code for the failure.
    """

    def __init__(self, response: _ResponseType, message: Optional[Union[str, Dict[str, Any]]]):
        self.response: _ResponseType = response
        self.status: int = response.status  # type: ignore
        self.code: int
        self.text: str
        if isinstance(message, dict):
            self.code = message.get('code', 0)
            base = message.get('message', '')
            errors = message.get('errors')
            if errors:
                errors = _flatten_error_dict(errors)
                helpful = '\n'.join('In %s: %s' % t for t in errors.items())
                self.text = base + '\n' + helpful
            else:
                self.text = base
        else:
            self.text = message or ''
            self.code = 0

        fmt = '{0.status} {0.reason} (error code: {1})'
        if len(self.text):
            fmt += ': {2}'

        super().__init__(fmt.format(self.response, self.code, self.text))


class Forbidden(HTTPException):
    """Exception that's raised for when status code 403 occurs.

    Subclass of :exc:`HTTPException`
    """

    pass


class NotFound(HTTPException):
    """Exception that's raised for when status code 404 occurs.

    Subclass of :exc:`HTTPException`
    """

    pass


class DiscordServerError(HTTPException):
    """Exception that's raised for when a 500 range status code occurs.

    Subclass of :exc:`HTTPException`.

    .. versionadded:: 1.5
    """

    pass


class InvalidData(ClientException):
    """Exception that's raised when the library encounters unknown
    or invalid data from Discord.
    """

    pass


class InvalidArgument(ClientException):
    """Exception that's raised when an argument to a function
    is invalid some way (e.g. wrong value or wrong type).

    This could be considered the analogous of ``ValueError`` and
    ``TypeError`` except inherited from :exc:`ClientException` and thus
    :exc:`DiscordException`.
    """

    pass


class LoginFailure(ClientException):
    """Exception that's raised when the :meth:`Client.login` function
    fails to log you in from improper credentials or some other misc.
    failure.
    """

    pass


class ConnectionClosed(ClientException):
    """Exception that's raised when the gateway connection is
    closed for reasons that could not be handled internally.

    Attributes
    -----------
    code: :class:`int`
        The close code of the websocket.
    reason: :class:`str`
        The reason provided for the closure.
    shard_id: Optional[:class:`int`]
        The shard ID that got closed if applicable.
    """

    def __init__(self, socket: ClientWebSocketResponse, *, shard_id: Optional[int], code: Optional[int] = None):
        # This exception is just the same exception except
        # reconfigured to subclass ClientException for users
        self.code: int = code or socket.close_code or -1
        # aiohttp doesn't seem to consistently provide close reason
        self.reason: str = ''
        self.shard_id: Optional[int] = shard_id
        super().__init__(f'Shard ID {self.shard_id} WebSocket closed with {self.code}')


class PrivilegedIntentsRequired(ClientException):
    """Exception that's raised when the gateway is requesting privileged intents
    but they're not ticked in the developer page yet.

    Go to https://discord.com/developers/applications/ and enable the intents
    that are required. Currently these are as follows:

    - :attr:`Intents.members`
    - :attr:`Intents.presences`

    Attributes
    -----------
    shard_id: Optional[:class:`int`]
        The shard ID that got closed if applicable.
    """

    def __init__(self, shard_id: Optional[int]):
        self.shard_id: Optional[int] = shard_id
        msg = (
            'Shard ID %s is requesting privileged intents that have not been explicitly enabled in the '
            'developer portal. It is recommended to go to https://discord.com/developers/applications/ '
            'and explicitly enable the privileged intents within your application\'s page. If this is not '
            'possible, then consider disabling the privileged intents instead.'
        )
        super().__init__(msg % shard_id)

class InvalidLength(InvalidArgument):
    """Exception that is raised when the lenght of a string parameter is invalid"""
    def __init__(self, my_name, _min=None, _max=None, *args: object) -> None:
        if _min is not None and _max is not None:
            err = "Length of '" + my_name + "' must be between " + str(_min) + " and " + str(_max)
        elif _min is None and _max is not None:
            err = "Length of '" + my_name + "' must be less than " + str(_max)
        elif _min is not None and _max is None:
            err = "Lenght of '" + my_name + "' must be more than " + str(_min)
        super().__init__(err)
class OutOfValidRange(InvalidArgument):
    """Exception that is raised when a value was out of its valid range"""
    def __init__(self, name, _min, _max, *args: object) -> None:
        super().__init__("'" + name + "' must be in range " + str(_min) + " and " + str(_max))
class WrongType(TypeError):
    """Exception that is raised when a parameter is of the wrong type"""
    def __init__(self, name, me, valid_type, *args: object) -> None:
        super().__init__("'" + name + "' must be of type " + (str(valid_type) if not isinstance(valid_type, list) else ' or '.join(valid_type)) + ", not " + str(type(me)))
class InvalidEvent(InvalidArgument):
    """Exceptioon that is raised when an invalid eventname was passed"""
    def __init__(self, name, events, *args: object) -> None:
        super().__init__("Invalid event name, event must be " + " or ".join(events) + ", not " + str(name))
class MissingListenedComponentParameters(ClientException):
    """Exception is raised whenever a callback for a listening component is missing parameters.
    
    The callback has to accept one argument#.
    """
    def __init__(self, *args: object) -> None:
        super().__init__("Callback function for listening components needs to accept one parameter (the used component)", *args)
class CouldNotParse(ClientException):
    """Exception that is raised when the libary was unable to parse a value with the given method"""
    def __init__(self, data, type, method, *args: object) -> None:
        super().__init__("Could not parse '" + str(data) + " [" + str(type) + "]' with method " + str(method), *args)