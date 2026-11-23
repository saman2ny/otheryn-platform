"""Platform models package - shared across all specialty products.

These re-export from the existing app.models package to maintain backwards compatibility
while establishing the platform architecture pattern.
"""

# Re-export platform models from app.models
from app.models.clinic import Clinic
from app.models.user import User
from app.models.healthcare import (
    AuditEvent,
    ClinicBranch,
    CommunicationOutbox,
    CommunicationTemplate,
    EmailOutbox,
    HealthRecord,
    HealthRecordRevision,
    InsuranceClaim,
    IntegrationConnection,
    IntegrationSyncJob,
    Patient,
    PatientCommunication,
    PatientEnquiry,
    PatientPortalAccount,
    PatientRecordShare,
    PatientVisit,
    PmsReconciliationRun,
    PmsReconciliationRow,
    RecallAutomationSettings,
    RecallReminder,
    RecordConsent,
    StaffInvitation,
    TreatmentLedgerEntry,
)
from app.models.organization import (
    ClinicOrganization,
    OrganizationInvitation,
    OrganizationMember,
)

__all__ = [
    "Clinic",
    "ClinicBranch",
    "StaffInvitation",
    "User",
    "ClinicOrganization",
    "OrganizationInvitation",
    "OrganizationMember",
    "Patient",
    "PatientEnquiry",
    "PatientCommunication",
    "PatientVisit",
    "PatientPortalAccount",
    "PatientRecordShare",
    "RecordConsent",
    "AuditEvent",
    "HealthRecord",
    "HealthRecordRevision",
    "IntegrationConnection",
    "IntegrationSyncJob",
    "InsuranceClaim",
    "PmsReconciliationRun",
    "PmsReconciliationRow",
    "TreatmentLedgerEntry",
    "RecallAutomationSettings",
    "RecallReminder",
    "CommunicationOutbox",
    "CommunicationTemplate",
    "EmailOutbox",
]