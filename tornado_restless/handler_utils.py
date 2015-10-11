from json import loads
from urllib.parse import parse_qs

from sqlalchemy.util import memoized_instancemethod
from tornado.web import HTTPError


@memoized_instancemethod
def get_content_encoding(handler, default='utf-8') -> str:
    """
    Get the encoding the client sends us for encoding request.body correctly

    :reqheader Content-Type: Provide a charset in addition for decoding arguments.
    """

    content_type_args = {k.strip(): v for k, v in parse_qs(handler.request.headers['Content-Type']).items()}
    if 'charset' in content_type_args and content_type_args['charset']:
        return content_type_args['charset'][0]
    else:
        return default
    
@memoized_instancemethod
def get_body_arguments(handler) -> dict:
    """
        Get arguments encode as json body

        :statuscode 415: Content-Type mismatch

        :reqheader Content-Type: application/x-www-form-urlencoded or application/json
    """

    content_type = handler.request.headers.get('Content-Type')
    if content_type is None:
        return {}
    
    if 'www-form-urlencoded' in content_type:
        payload = handler.request.arguments
        for key, value in payload.items():
            if len(value) == 0:
                payload[key] = None
            elif len(value) == 1:
                payload[key] = str(value[0], encoding=get_content_encoding(handler))
            else:
                payload[key] = [str(value, encoding=get_content_encoding(handler)) for value in value]
        return payload
    elif 'application/json' in content_type:
        return loads(str(handler.request.body, encoding=get_content_encoding(handler)))
    else:
        raise HTTPError(415, content_type=content_type)
