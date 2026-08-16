# Python Common Patterns

Reference patterns for this project. Load when generating code that uses these structures.

## Table of Contents
1. [Python: Pydantic Models](#python-pydantic-models)
2. [Python: Controllers (Flask / flask-openapi3)](#python-controllers-flask--flask-openapi3)
3. [Python: Services](#python-services)
4. [Python: Clients (HTTP)](#python-clients-http)
5. [Python: Repositories (SQLite)](#python-repositories-sqlite)
6. [Python: Exception Hierarchy](#python-exception-hierarchy)
7. [Python: Caching](#python-caching)
8. [Python: Testing](#python-testing)

---

## Python: Pydantic Models

### Standard field model — all fields optional with `Field(default=None, example=...)`

```python
from pydantic import BaseModel, Field
from typing import Optional

class DealPathVariables(BaseModel):
    deal_number: int = Field(description="The deal number to retrieve", example=102863944)

class SearchCriteria(BaseModel):
    deal_number: Optional[int] = Field(default=None, example=103669015)
    from_date: Optional[date] = Field(default=None)
    connection_name: Optional[str] = Field(default=None)
```

### Aliased fields — camelCase API ↔ snake_case Python

```python
from pydantic import BaseModel, Field
from typing import Optional

class AssociatedParty(BaseModel):
    entity_cis: Optional[str] = Field(default=None, alias="entityCIS")
    ap_cis: Optional[str] = Field(default=None, alias="apCIS")
    ap_role: Optional[str] = Field(default=None, alias="apRole")
```

Serialise with `model.model_dump(by_alias=True)` to emit camelCase.

### List wrapper — `RootModel[List[X]]`

```python
from pydantic import RootModel, BaseModel, Field
from typing import List, Optional

class Arrangement(BaseModel):
    id: Optional[str] = Field(default=None, alias="arrangementId")

class ArrangementList(RootModel[List[Arrangement]]):
    pass
```

Use `RootModel` whenever an endpoint returns a bare JSON array. Never wrap in a dict.

### Computed fields and private attributes

```python
from pydantic import BaseModel, Field, PrivateAttr, computed_field
from typing import Optional

class Customer(BaseModel):
    name: Optional[str] = Field(default=None)
    _total_limit: Optional[int] = PrivateAttr(default=None)  # not serialised

    @computed_field(alias="type")
    @property
    def computed_type(self) -> Optional[str]:
        if self.name is None:
            return None
        return "Organisation" if self.name.startswith("*") else "Individual"

    @computed_field
    @property
    def total_limit(self) -> Optional[int]:
        if self._total_limit is None:
            return None
        return int(str(self._total_limit).lstrip("$").replace(",", ""))
```

### Nested default factory

```python
from pydantic import BaseModel, Field
from typing import Optional

class PostFormat(BaseModel):
    group_id: Optional[str] = Field(default=None, alias="groupId")
    # Use default_factory for mutable defaults (list, nested model)
    rm_details: Optional[RMDetails] = Field(default_factory=RMDetails)
    entities: List[Entity] = Field(default_factory=list)
```

---

## Python: Controllers (Flask / flask-openapi3)

The project uses `flask-openapi3` `APIBlueprint`. Controllers are classes; routes are closures inside `__init__`.

```python
from http import HTTPStatus
import logging
from flask_openapi3 import APIBlueprint, Tag
from models.path_variables import DealPathVariables
from models.post_format import PostFormat, PostFormatList
from services.post import PostService

log = logging.getLogger(__name__)

class PostController:
    def __init__(self, post_service: PostService, default_errors: dict):
        tag = Tag(name="Post Creator", description="Post format endpoints")
        self.blueprint = APIBlueprint('post', __name__, url_prefix="/post",
                                      abp_tags=[tag], abp_responses=default_errors)
        self.post_service = post_service

        @self.blueprint.get("/<int:deal_number>", responses={HTTPStatus.OK: PostFormat})
        def get_post(path: DealPathVariables) -> PostFormat:
            """
                Get Post Format
                Build POST format for a given deal number
            """
            result = self.post_service.build_post(path.deal_number)
            return result.model_dump(by_alias=True), HTTPStatus.OK

        @self.blueprint.get("/", responses={HTTPStatus.OK: PostFormatList})
        def get_all_posts() -> PostFormatList:
            """
                All Posts
                Get all available post formats
            """
            results = self.post_service.get_all()
            return [r.model_dump(by_alias=True) for r in results.root], HTTPStatus.OK
```

**Rules:**
- Return `(model.model_dump(...), HTTPStatus.CODE)` — never return the model directly
- Path variables: typed path model passed as `path:` parameter
- Query variables: typed query model passed as `query:` parameter
- Always log at `warning` or above when returning non-2xx

---

## Python: Services

Services are thin orchestration classes. They delegate to clients; they do NOT call `requests` directly.

```python
from clients.gcm.client import GcmClient
from clients.gcm.models.customer_profile import CustomerProfile
from clients.gcm.models.customer_relationships import CustomerInterrelationshipsList
import logging

log = logging.getLogger(__name__)

class GcmService:
    def __init__(self, gcm_client: GcmClient):
        self.gcm_client = gcm_client

    def fetch_customer_profile(self, customer_id: str, customer_type: str,
                               brand_silo: str) -> CustomerProfile:
        return self.gcm_client.fetch_customer_profile(customer_id, customer_type, brand_silo)

    def fetch_customer_relationships(self, customer_id: str, customer_type: str,
                                     brand_silo: str) -> CustomerInterrelationshipsList:
        return self.gcm_client.fetch_customer_relationships(customer_id, customer_type, brand_silo)
```

**Rules:**
- Constructor receives client via dependency injection — never instantiate clients inside a service
- Return typed models from client, not raw dicts or `requests.Response`
- Log errors at `log.error(...)` before re-raising or returning empty defaults
- Services that aggregate multiple clients (like `PostService`) compose them in `__init__`

---

## Python: Clients (HTTP)

Clients own all `requests` usage. They inject headers via a custom `HTTPAdapter` subclass and apply `@cache` for repeated reads.

```python
import os
import uuid
import requests
from requests.adapters import HTTPAdapter
from clients.gcm.models.customer_profile import CustomerProfile
from helper.cache import cache
import logging

log = logging.getLogger(__name__)

class GcmClient:
    def __init__(self):
        self.base_url = os.environ['GCM_BASE_URL']
        self.username = os.environ['GCM_USERNAME']
        self.password = os.environ['GCM_PASSWORD']
        self.session = requests.Session()

        class RequestHeaderInterceptor(HTTPAdapter):
            def send(self, request, **kwargs):
                request.headers.update({
                    "x-messageId": str(uuid.uuid4()),
                    "x-appCorrelationId": str(uuid.uuid4()),
                    "x-organisationId": "SGB",
                    "Content-Type": "application/json",
                })
                return super().send(request, **kwargs)

        self.session.mount('http://', RequestHeaderInterceptor())
        self.session.mount('https://', RequestHeaderInterceptor())

    @cache(minutes=5)
    def fetch_customer_profile(self, customer_id: str, customer_type: str,
                               brand_silo: str) -> CustomerProfile:
        response = self.session.get(
            url=f"{self.base_url}/customers/{customer_id}/profile",
            params={"idScheme": "CustomerInternalId", "brandSilo": brand_silo},
            auth=(self.username, self.password),
        )
        response.raise_for_status()
        return CustomerProfile.model_validate(response.json())
```

**Rules:**
- All config from `os.environ[...]` — raise `KeyError` immediately if missing (fail-fast)
- Use `HTTPAdapter` subclass for headers that apply to every request
- Apply `@cache(minutes=N)` on read methods that hit slow upstream APIs
- Parse responses with `Model.model_validate(response.json())` — never return raw dicts
- Call `response.raise_for_status()` before parsing

---

## Python: Repositories (SQLite)

Repositories own all database access. Schema is built dynamically from upstream XML data shapes.

```python
import sqlite3
from typing import List
from repositories.tla.models.deal import Deal
import logging

log = logging.getLogger(__name__)

class TlaRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def prepare_database(self, data: dict[str, list[dict[str, str]]]) -> None:
        """Build tables dynamically from upstream XML key sets."""
        schema: dict[str, set] = {}
        for key, rows in data.items():
            schema.setdefault(key, set())
            for row in rows:
                schema[key].update(row.keys())

        for table_name, columns in schema.items():
            self._create_table(table_name, columns)
        for table_name, rows in data.items():
            for row in rows:
                self._insert(table_name, row)

    def _create_table(self, table_name: str, columns: set) -> None:
        cols = ", ".join(f"{c} TEXT" for c in columns)
        self.connection.execute(f"CREATE TABLE {table_name} ({cols})")
        self.connection.commit()

    def _insert(self, table_name: str, data: dict) -> None:
        placeholders = ", ".join("?" for _ in data)
        cols = ", ".join(data.keys())
        self.connection.execute(
            f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
            list(data.values())
        )
        self.connection.commit()
```

**Rules:**
- Constructor receives `sqlite3.Connection` — never open a connection inside a repository
- Private helpers prefixed with `_` — only public interface is exposed
- Use parameterised queries (`?` placeholders) — never f-string values into SQL

---

## Python: Exception Hierarchy

All custom exceptions inherit from `ExceptionBase` which carries `status_code` for the Flask error handler.

```python
class ExceptionBase(Exception):
    def __init__(self, message: str, details: any, status_code: int):
        super().__init__(message)
        self.message = message
        self.details = details
        self.status_code = status_code

class NotFoundException(ExceptionBase):
    def __init__(self, message: str, details=None):
        super().__init__(message, details, 404)

class UpstreamServiceException(ExceptionBase):
    """Raised when an upstream API returns 5xx or is unreachable."""
    def __init__(self, message: str, details=None):
        super().__init__(message, details, 502)

class UpstreamBadRequestException(ExceptionBase):
    """Raised when an upstream API returns 4xx (bad input we sent)."""
    def __init__(self, message: str, details=None):
        super().__init__(message, details, 502)

class BadRequestException(ExceptionBase):
    def __init__(self, message: str, details=None):
        super().__init__(message, details, 400)

class NotImplementedException(ExceptionBase):
    def __init__(self, message: str, details=None):
        super().__init__(message, details, 501)
```

**Usage:**
```python
# In a client — wrap upstream errors
try:
    response.raise_for_status()
except requests.HTTPError as e:
    if e.response.status_code >= 500:
        raise UpstreamServiceException(f"GCM returned {e.response.status_code}", details=str(e))
    raise UpstreamBadRequestException(f"GCM rejected request", details=str(e))
```

---

## Python: Caching

`@cache(minutes=N)` is a time-expiring LRU cache from `helper.cache`. Apply to client read methods.

```python
from helper.cache import cache

class GcmClient:
    @cache(minutes=5)
    def fetch_customer_profile(self, customer_id: str, customer_type: str,
                               brand_silo: str) -> CustomerProfile:
        # result cached for 5 minutes per unique argument combination
        ...
```

**Rules:**
- Only cache read operations — never cache mutating calls
- Cache is cleared on TTL expiry, not on write — suitable for data that changes infrequently
- Arguments must be hashable (strings, ints) — do not pass dicts or lists as cached method args
- Exceptions are NOT cached — a failed call will retry on the next request

---

## Python: Testing

### `conftest.py` — path setup and env loading

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Make source importable without installing the package
orchestrator_dir = Path(__file__).parent.parent
sys.path.insert(0, str(orchestrator_dir))

env_file = os.getenv('ENV_FILE', '.env.dev')
load_dotenv(orchestrator_dir / env_file)
os.environ['ENV_FILE'] = env_file  # propagate to subprocesses
```

### Unit test — model structure

```python
import pytest

def test_entity_model_import():
    from models.entity import Entity
    assert Entity is not None

def test_arrangement_list_is_root_model():
    from models.arrangements import ArrangementList
    result = ArrangementList.model_validate([{"arrangementId": "A001"}])
    assert len(result.root) == 1
    assert result.root[0].id == "A001"
```

### Integration test — live server + Playwright

```python
from utils.post_creator_instance import PostCreatorInstance
from playwright.sync_api import sync_playwright

class TestJsonViewPage:
    def test_full_data(self, httpserver):
        instance = PostCreatorInstance()
        instance.poll_server_uptime()  # raises RuntimeError if server doesn't start

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"http://localhost:{instance.port}/")
            # assert UI state...
        
        instance.stop()
```

**Rules:**
- `PostCreatorInstance` selects a random free port via `socket` to avoid port conflicts
- `poll_server_uptime()` retries 5× with 1s sleep — raises `RuntimeError` on timeout
- Use `pytest-httpserver` (`HTTPServer`) to mock upstream HTTP dependencies in integration tests
