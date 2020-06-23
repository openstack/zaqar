# Copyright (c) 2020 Fiberhome Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Encryption has a dependency on the pycrypto. If pycrypto is not available,
CryptoUnavailableError will be raised.

"""

import base64
import functools
import hashlib
import os
import pickle

try:
    from cryptography.hazmat import backends as crypto_backends
    from cryptography.hazmat.primitives import ciphers
    from cryptography.hazmat.primitives.ciphers import algorithms
    from cryptography.hazmat.primitives.ciphers import modes
    from cryptography.hazmat.primitives import padding
except ImportError:
    ciphers = None

from zaqar.conf import transport
from zaqar.i18n import _


class EncryptionFailed(ValueError):
    """Encryption failed when encrypting messages."""

    def __init__(self, msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        super(EncryptionFailed, self).__init__(msg)


class DecryptError(Exception):
    """raise when unable to decrypt encrypted data."""
    pass


class CryptoUnavailableError(Exception):
    """raise when Python Crypto module is not available."""
    pass


def assert_crypto_availability(f):
    """Ensure cryptography module is available."""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        if ciphers is None:
            raise CryptoUnavailableError()
        return f(*args, **kwds)
    return wrapper


class EncryptionFactory(object):

    def __init__(self, conf):
        self._conf = conf
        self._conf.register_opts(transport.ALL_OPTS,
                                 group=transport.GROUP_NAME)
        self._limits_conf = self._conf[transport.GROUP_NAME]
        self._algorithm = self._limits_conf.message_encryption_algorithms
        self._encryption_key = None
        if self._limits_conf.message_encryption_key:
            hash_function = hashlib.sha256()
            key = bytes(self._limits_conf.message_encryption_key, 'utf-8')
            hash_function.update(key)
            self._encryption_key = hash_function.digest()

    def getEncryptor(self):
        if self._algorithm == 'AES256' and self._encryption_key:
            return AES256Encryptor(self._encryption_key)


class Encryptor(object):

    def __init__(self, encryption_key):
        self._encryption_key = encryption_key

    def message_encrypted(self, messages):
        """Encrypting a list of messages.

        :param messages: A list of messages
        """
        pass

    def message_decrypted(self, messages):
        """decrypting a list of messages.

        :param messages: A list of messages
        """
        pass

    def get_cipher(self):
        pass

    def get_encryption_key(self):
        return self._encryption_key


class AES256Encryptor(Encryptor):

    def get_cipher(self):
        iv = os.urandom(16)
        cipher = ciphers.Cipher(
            algorithms.AES(self.get_encryption_key()),
            modes.CBC(iv), backend=crypto_backends.default_backend())
        # AES algorithm uses block size of 16 bytes = 128 bits, defined in
        # algorithms.AES.block_size. Using ``cryptography``, we will
        # analogously use hazmat.primitives.padding to pad it to
        # the 128-bit block size.
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        return iv, cipher, padder

    def _encrypt_string_message(self, message):
        """Encrypt the message type of string"""
        message = message.encode('utf-8')
        iv, cipher, padder = self.get_cipher()
        encryptor = cipher.encryptor()
        padded_data = padder.update(message) + padder.finalize()
        data = iv + encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(data)

    def _encrypt_other_types_message(self, message):
        """Encrypt the message type of other types"""
        iv, cipher, padder = self.get_cipher()
        encryptor = cipher.encryptor()
        padded_data = padder.update(message) + padder.finalize()
        data = iv + encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(data)

    def _encrypt_message(self, message):
        """Encrypt the message data with the given secret key.

        Padding is n bytes of the value n, where 1 <= n <= blocksize.
        """
        if isinstance(message['body'], str):
            message['body'] = self._encrypt_string_message(message['body'])
        else:
            # For other types like dict or list, we need to serialize them
            # first.
            try:
                s_message = pickle.dumps(message['body'])
            except pickle.PickleError:
                return
            message['body'] = self._encrypt_other_types_message(s_message)

    def _decrypt_message(self, message):
        try:
            encrypted_message = base64.b64decode(message['body'])
        except (ValueError, TypeError):
            return
        iv = encrypted_message[:16]
        cipher = ciphers.Cipher(
            algorithms.AES(self._encryption_key),
            modes.CBC(iv),
            backend=crypto_backends.default_backend())
        try:
            decryptor = cipher.decryptor()
            data = (decryptor.update(encrypted_message[16:]) +
                    decryptor.finalize())
        except Exception:
            raise DecryptError(_('Encrypted data appears to be corrupted.'))

        # Strip the last n padding bytes where n is the last value in
        # the plaintext
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(data) + unpadder.finalize()
        try:
            message['body'] = pickle.loads(data)
        except pickle.UnpicklingError:
            # If the data is a string which didn't be serialized, there will
            # raise an exception. We just try to return the string itself.
            message['body'] = str(data, encoding="utf-8")

    @assert_crypto_availability
    def message_encrypted(self, messages):
        """Encrypting a list of messages.

        :param messages: A list of messages
        """
        if self.get_encryption_key():
            for msg in messages:
                self._encrypt_message(msg)
        else:
            msg = _(u'Now Zaqar only support AES-256 and need to specify the'
                    u'key.')
            raise EncryptionFailed(msg)

    @assert_crypto_availability
    def message_decrypted(self, messages):
        """decrypting a list of messages.

        :param messages: A list of messages
        """
        if self.get_encryption_key():
            for msg in messages:
                self._decrypt_message(msg)
        else:
            msg = _(u'Now Zaqar only support AES-256 and need to specify the'
                    u'key.')
            raise EncryptionFailed(msg)
