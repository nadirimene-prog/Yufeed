"""
Factory Boy factories for legal document and user models.
"""

import factory
from factory.faker import Faker
from datetime import datetime
import uuid

from src.models.models import LegalDocument, DocType, ComplianceDomain, RiskLevel
from src.models.tenant_models import Tenant


class BaseSQLAlchemyFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory that accepts sqlalchemy_session in create kwargs."""

    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = kwargs.pop("sqlalchemy_session", None)
        if session is not None:
            cls._meta.sqlalchemy_session = session
        return super()._create(model_class, *args, **kwargs)


class LegalDocumentFactory(BaseSQLAlchemyFactory):
    """Factory for creating test LegalDocument instances."""

    class Meta:
        model = LegalDocument
        sqlalchemy_session_persistence = "commit"

    celex = factory.LazyFunction(
        lambda: f"3{factory.Faker('year').generate()}R{factory.Faker('random_int', min=1000, max=9999).generate()}"
    )
    eli = factory.LazyFunction(lambda: f"http://data.europa.eu/eli/reg/{uuid.uuid4().hex[:8]}")
    cellar_id = factory.LazyFunction(lambda: f"cellar_{uuid.uuid4().hex[:16]}")
    title = factory.Faker("sentence", nb_words=10)
    type = factory.Faker("random_element", elements=[e.value for e in DocType])
    publication_date = factory.Faker("date_time_between", start_date="-5y", end_date="now")
    compliance_domains = factory.LazyFunction(
        lambda: [
            factory.Faker("random_element", elements=[e.value for e in ComplianceDomain]).generate()
        ]
    )
    risk_level = factory.Faker("random_element", elements=[e.value for e in RiskLevel])
    summary = factory.Faker("paragraph")
    full_text = factory.Faker("text", max_nb_chars=5000)

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class UserFactory(factory.Factory):
    """Factory for creating test user data (for auth tests)."""

    class Meta:
        model = dict

    email = factory.Faker("email")
    password = "TestPassword123!"
    full_name = factory.Faker("name")
    role = factory.Faker("random_element", elements=["user", "analyst", "admin"])


class TenantFactory(BaseSQLAlchemyFactory):
    """Factory for creating test Tenant instances."""

    class Meta:
        model = Tenant
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyFunction(lambda: f"tenant_{uuid.uuid4().hex[:8]}")
    name = factory.Faker("company")
    display_name = factory.Faker("company")
    is_active = True
    tier = "standard"
