import datetime

from sqlmodel import TIMESTAMP, Column, Field, Relationship, SQLModel, text


class Service(SQLModel, table=True):
    """A service is representative of a namespace reserved by an SDK application."""

    id: int | None = Field(default=None, primary_key=True)
    service_name: str = Field(index=True, unique=True, nullable=False, min_length=3, max_length=63)
    """The namespace your service takes up on this system. You can spin up multiple processes on multiple different machines with this key, but this will horizontally scale.
    
    This is the only value which can be explicitly set by a user. The field's validation is more thoroughly checked on the UI side.
    """
    username: str = Field(nullable=False)
    """This is the username associated with the registry service's main authentication mechanism. It is ESSENTIAL that only authorized users can reserve Service namespaces.
    
    At the moment, we don't really need to associate any additional information with a user in our own database (we don't store user passwords), as we'll rely on another authentication server to store user information.
    However, if this service was completely standalone, we would probably want to have this field be a foreign key.

    It's possible that we may want to allow multiple users to manage the API keys in the future.
    """
    api_key: str = Field(nullable=False)
    """The form of authentication to verify that your SDK application controls the Service.
    
    This value is always created by the server, though users are allowed to choose when to rotate the value.
    """
    created_on: datetime.datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text('CURRENT_TIMESTAMP'),
        )
    )
    last_modified: datetime.datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text('CURRENT_TIMESTAMP'),
            server_onupdate=text('CURRENT_TIMESTAMP'),
        )
    )

    brokers: list['Broker'] = Relationship(back_populates='service', cascade_delete=True)  # noqa: F821
