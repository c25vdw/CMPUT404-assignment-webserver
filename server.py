#  coding: utf-8
import socketserver

from os import path
# Copyright 2021 Lucas Zeng
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The file is templated from its forked project, which belongs to:
# Copyright 2013 Abram Hindle, Eddie Antonio Santos
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Furthermore it is derived from the Python documentation examples thus
# some of the code is Copyright © 2001-2013 Python Software
# Foundation; All Rights Reserved
#
# http://docs.python.org/2/library/socketserver.html
#
# run: python freetests.py

# try: curl -v -X GET http://127.0.0.1:8080/


class HTTPError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


# HTTP codes handled as exception
class ServerException(HTTPError):
    # 500+
    pass


class ClientException(HTTPError):
    # 400+
    pass


class RedirectException(HTTPError):
    # 300+
    def __init__(self, code, message, location):
        super().__init__(code, message)
        self.location = location


class NotFoundException(ClientException):
    # 404
    def __init__(self, code=404, message="Not Found"):
        super().__init__(code, message)

# helpers


def rel_to_abs(root, rel):
    return path.join(root, *rel.split('/'))


class MyWebServer(socketserver.BaseRequestHandler):

    ROOT = 'www'
    MIME_EXT = ['html', 'javascript', 'css']
    NOT_FOUND_RESPONSE = b"""<!DOCTYPE html>
    <html>
        <body>
        <h2>404. The resource is not found &#128575;</h2>
        </body>
    </html>
"""

    root_path = path.join(path.dirname(path.realpath('__file__')), ROOT)

    def handle(self):
        self.data = self.request.recv(1024).strip()

        response = b''
        try:
            # parse url path, raise 405 if method not allowed
            resource_url_path = self.get_url_path(self.data).decode('utf-8')
            # parse file path of the resource, raise 404 or 301
            resource_file_path = self.get_file_path(resource_url_path)
            # read from file, raise 404
            file_bytes = self.read_bytes_from_file(resource_file_path)
            # dump to bytes buffer
            response = self.dump_response(file_bytes, resource_file_path)
        except NotFoundException:
            response = self.dump_404()
        except RedirectException as err:
            response = self.dump_301(err)
        except (ClientException, ServerException) as err:
            response = ('HTTP/1.1 %s %s' %
                        (err.code, err.message)).encode('utf-8')

        self.request.sendall(response)

    def dump_404(self):
        res = b'HTTP/1.1 404 Not Found'
        res += f"""
Content-Type: text/html
Content-Length: {len(self.NOT_FOUND_RESPONSE)}

""".encode('utf-8')
        res += self.NOT_FOUND_RESPONSE
        return res

    def dump_301(self, err):
        res = b'HTTP/1.1 301 Moved Permanently'
        res += f"""
Location: {err.location}
Content-Length: 0

""".encode('utf-8')
        return res

    def dump_response(self, file_bytes, resource_url_path):
        file_type = resource_url_path.rsplit('.')[-1]
        if file_type not in self.MIME_EXT:
            file_type = 'plain'
        res = b'HTTP/1.1 200 OK'
        res += f"""
Content-Type: text/{file_type}
Content-Length: {len(file_bytes)}

""".encode('utf-8')
        res += file_bytes
        return res

    def get_file_path(self, url_path):
        def fail_on_bad_file_path(file_path):
            if not path.exists(file_path):
                raise NotFoundException()
            if not self.root_path == path.commonpath([self.root_path, file_path]):
                raise NotFoundException(404, "Don't trick me")

        if url_path.endswith('/'):
            # see if the slashed path has index.html root
            file_path = rel_to_abs(self.root_path, url_path + 'index.html')
            return file_path
        elif all(map(lambda mime_ext: not url_path.endswith('.' + mime_ext), self.MIME_EXT)):
            # the path doesn't ends with a slash, nor does it have any supported extension
            # try redirect to slashed path
            fail_on_bad_file_path(rel_to_abs(self.root_path, url_path + '/'))
            raise RedirectException(301, "Found", url_path + '/')
        else:
            # a normal file path with extension, try serve it directly
            file_path = rel_to_abs(self.root_path, url_path)
            fail_on_bad_file_path(file_path)
            return file_path

    def read_bytes_from_file(self, file_path):
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except:
            print("cannot open file at >>", file_path)
            raise ServerException(500, "failed to read file")

    def get_url_path(self, buf):
        # buf: byte string
        for line in buf.split(b"\r\n"):
            if line.startswith(b'GET') or line.startswith(b'HEAD'):
                words = line.strip().split(b' ')
                return words[1]  # "GET >>>/some_resource<<<< HTTP/1.1"
        raise ClientException(405, "Method Not Allowed")


if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
