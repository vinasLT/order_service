from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetUserRequest(_message.Message):
    __slots__ = ("user_uuid",)
    USER_UUID_FIELD_NUMBER: _ClassVar[int]
    user_uuid: str
    def __init__(self, user_uuid: _Optional[str] = ...) -> None: ...

class GetUserResponse(_message.Message):
    __slots__ = ("first_name", "last_name", "language", "email", "username", "phone_number", "is_active", "phone_verified", "email_verified", "address")
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    PHONE_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    EMAIL_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    first_name: str
    last_name: str
    language: str
    email: str
    username: str
    phone_number: str
    is_active: bool
    phone_verified: bool
    email_verified: bool
    address: Address
    def __init__(self, first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., language: _Optional[str] = ..., email: _Optional[str] = ..., username: _Optional[str] = ..., phone_number: _Optional[str] = ..., is_active: bool = ..., phone_verified: bool = ..., email_verified: bool = ..., address: _Optional[_Union[Address, _Mapping]] = ...) -> None: ...

class Address(_message.Message):
    __slots__ = ("country", "state", "zip_code", "city", "address")
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ZIP_CODE_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    country: str
    state: str
    zip_code: int
    city: str
    address: str
    def __init__(self, country: _Optional[str] = ..., state: _Optional[str] = ..., zip_code: _Optional[int] = ..., city: _Optional[str] = ..., address: _Optional[str] = ...) -> None: ...
