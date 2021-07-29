# Copyright (c) 2021 The Trade Desk, Inc
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Internal module for keeping facilities related to encryption keys.

Do not use this module directly, import from uid2_client instead, e.g.
>>> from uid2_client import EncryptionKeysCollection
"""


import datetime as dt
from bisect import bisect_right


class EncryptionKey:
    """Wrapper class for keeping data about an encryption key.

    Attrs:
        key_id (int): identifier of the key
        site_id (int): id of the site the key belongs to
        created (datetime): UTC date/time for when the key was created
        activates (datetime): UTC date/time for when the key becomes active
        expires (datetime): UTC date/time for when the key expires
        secret (bytes): the actual encryption key
    """

    def __init__(self, key_id, site_id, created, activates, expires, secret):
        """Create a new encryption key."""
        self._id = key_id
        self._site_id = site_id
        self._created = created
        self._activates = activates
        self._expires = expires
        self._secret = secret


    @property
    def key_id(self):
        """int: Unique identifier of the key."""
        return self._id


    @property
    def site_id(self):
        """int: id of the site the key belongs to."""
        return self._site_id


    @property
    def created(self):
        """datetime: UTC date/time for when the key was created."""
        return self._created


    @property
    def activates(self):
        """datetime: UTC date/time for when the key becomes active."""
        return self._activates


    @property
    def expires(self):
        """datetime: UTC date/time for when the key expires."""
        return self._expires


    @property
    def secret(self):
        """bytes: encryption key data. """
        return self._secret


    def is_active(self, now):
        """Whether the key is active at the specified time."""
        return self._activates <= now and now < self._expires


class _SiteKeyActivatesList:
    """Internal wrapper for list of site keys."""

    def __init__(self, site_keys):
        self._site_keys = site_keys


    def __len__(self):
        return len(self._site_keys)


    def __getitem__(self, i):
        return self._site_keys[i].activates


class EncryptionKeysCollection:
    """A collection of EncryptionKey objects.

    This is a dictionary like immutable collection object containing encryption keys
    used for decoding UID2 advertising tokens.
    """

    def __init__(self, keys):
        self._latest_expires = None
        self._keys = dict()
        self._keys_by_site = dict()
        for key in keys:
            self._keys[key.key_id] = key
            if key.site_id > 0:
                self._keys_by_site.setdefault(key.site_id, []).append(key)
            if self._latest_expires is None or key.expires > self._latest_expires:
                self._latest_expires = key.expires
        for _, site_keys in self._keys_by_site.items():
            site_keys.sort(key=lambda x: x.activates)


    def __len__(self):
        return len(self._keys)


    def __contains__(self, key_id):
        return key_id in self._keys.keys()


    def __getitem__(self, key_id):
        return self._keys[key_id]


    def get(self, key_id, default=None):
        """Get encryption key with the specified id, else default."""
        return self._keys.get(key_id, default)


    def key_ids(self):
        """Get list of ids of the keys available in the collection."""
        return self._keys.keys()


    def values(self):
        """Get all encryption keys in the collection as a list."""
        return self._keys.values()


    def get_active_site_key(self, site_id, now):
        """Get active encryption key for the specified site, else None.

        Args:
            site_id (int): ID of the site to get the key for
            now (datetime): date/time to use as timestamp to determine whether the key is active

        Returns:
            EncryptionKey: active site key or None
        """
        site_keys = self._keys_by_site.get(site_id)
        if site_keys is None or len(site_keys) == 0:
            return None
        i = bisect_right(_SiteKeyActivatesList(site_keys), now)
        while i > 0:
            i -= 1
            key = site_keys[i]
            if key.is_active(now):
                return key
        return None


    def valid(self, now):
        """Check whether the collection is valid.

        Collection is considered valid if at least one key has expiry date/time after now."""
        return self._latest_expires is not None and self._latest_expires > now
