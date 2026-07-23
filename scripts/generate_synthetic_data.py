import argparse
import json
from pathlib import Path


OUTPUT_PATH = Path("data/synthetic/enterprise_knowledge_base.jsonl")

TOPICS = [
    {
        "key": "vpn",
        "title": "VPN tunnel fails after MFA approval",
        "category": "it_support",
        "department": "it",
        "tags": ["vpn", "mfa", "network"],
        "symptom": "VPN authentication succeeds after MFA but the tunnel does not establish",
        "root_cause": "a stale VPN profile created before gateway certificate rotation",
        "resolution": "refresh the VPN profile, update the client, flush DNS, and retry from a trusted network",
        "escalation": "Network Operations",
    },
    {
        "key": "password",
        "title": "Repeated password lockout after reset",
        "category": "it_support",
        "department": "it",
        "tags": ["password", "identity", "account-lockout"],
        "symptom": "the user is locked again shortly after a successful password reset",
        "root_cause": "cached credentials on an old mobile mail profile",
        "resolution": "remove stale profiles, revoke active sessions, unlock the account, and sign in again",
        "escalation": "Identity Operations",
    },
    {
        "key": "email-dlp",
        "title": "Outbound email delayed by DLP review",
        "category": "security",
        "department": "security",
        "tags": ["email", "dlp", "vendor"],
        "symptom": "approved vendor email remains queued for review",
        "root_cause": "attachments matched a sensitive finance export pattern",
        "resolution": "verify vendor approval, release the message, and update the approved transfer rule",
        "escalation": "Security Operations",
    },
    {
        "key": "database-access",
        "title": "Database access request missing owner approval",
        "category": "data_access",
        "department": "data_platform",
        "tags": ["database", "access", "approval"],
        "symptom": "access to a curated schema is paused by support",
        "root_cause": "the request did not include data owner approval and expiration date",
        "resolution": "attach owner approval, business purpose, and a 30 to 90 day expiration",
        "escalation": "Data Platform",
    },
    {
        "key": "docker-build",
        "title": "Docker build fails on private package download",
        "category": "devops",
        "department": "platform",
        "tags": ["docker", "ci", "package-registry"],
        "symptom": "container build fails with a 401 response during dependency installation",
        "root_cause": "the package registry token expired after secret rotation",
        "resolution": "update the CI secret, rerun the build, and monitor future token expiry",
        "escalation": "Platform Engineering",
    },
    {
        "key": "kubernetes-crashloop",
        "title": "Kubernetes pod enters CrashLoopBackOff",
        "category": "devops",
        "department": "platform",
        "tags": ["kubernetes", "crashloopbackoff", "config"],
        "symptom": "a worker pod restarts repeatedly after deployment",
        "root_cause": "a config map value used text where an integer was required",
        "resolution": "correct the config map, restart the deployment, and validate Helm values",
        "escalation": "Platform Engineering",
    },
    {
        "key": "airflow-dag",
        "title": "Airflow DAG misses analytics SLA",
        "category": "data_engineering",
        "department": "data_engineering",
        "tags": ["airflow", "dag", "sla"],
        "symptom": "the daily analytics workflow misses the published dashboard SLA",
        "root_cause": "the upstream raw source table arrived late after maintenance",
        "resolution": "rerun the transform after source completion and add a source availability sensor",
        "escalation": "Data Engineering",
    },
    {
        "key": "backup",
        "title": "PostgreSQL scheduled backup fails",
        "category": "operations",
        "department": "data_platform",
        "tags": ["backup", "postgresql", "restore"],
        "symptom": "the scheduled database backup job reports failure",
        "root_cause": "backup storage capacity was exhausted before artifact upload",
        "resolution": "free storage, rerun the job, and validate that the backup artifact exists",
        "escalation": "Data Platform",
    },
    {
        "key": "cve-patching",
        "title": "High severity CVE patch response",
        "category": "security",
        "department": "security",
        "tags": ["cve", "patching", "vulnerability"],
        "symptom": "a managed service version is listed as affected by a high severity CVE",
        "root_cause": "the service runs a vulnerable component version",
        "resolution": "map affected services, test the patch in staging, deploy, and validate version",
        "escalation": "Security Operations",
    },
    {
        "key": "onboarding",
        "title": "Data engineering laptop onboarding incomplete",
        "category": "onboarding",
        "department": "data_engineering",
        "tags": ["onboarding", "laptop", "developer-setup"],
        "symptom": "a new engineer cannot run the local pipeline checks",
        "root_cause": "Docker Desktop and database client tools were not installed",
        "resolution": "install approved tools, request access, clone the onboarding repo, and run tests",
        "escalation": "Data Engineering Enablement",
    },
]

POLICIES = [
    ("mfa", "Multi-Factor Authentication Policy", "All users must use MFA for VPN, email, cloud consoles, and privileged systems. Exceptions require Security Operations approval and expire within 30 days."),
    ("backup-retention", "Backup Retention Policy", "Production database backups are retained for 35 days. Monthly compliance snapshots are retained for 13 months. Restore tests run quarterly."),
    ("cloud-access", "Cloud Console Access Policy", "Cloud console access requires manager approval, MFA, privileged access training, named accounts, and time-bound roles."),
    ("device-security", "Managed Device Security Policy", "Company devices must use disk encryption, endpoint protection, automatic patching, and screen lock controls."),
    ("incident-response", "Incident Response Policy", "Severity, impact, owner, timeline, mitigation, root cause, and prevention actions must be recorded for incidents."),
    ("vendor-access", "Vendor Access Policy", "Vendor access must be sponsored by an internal owner, time limited, logged, and reviewed after completion."),
    ("software-install", "Software Installation Policy", "Software must come from approved repositories or documented vendor sources and must not bypass endpoint controls."),
    ("privileged-access", "Privileged Access Policy", "Privileged roles require approval, MFA, break-glass logging, monthly review, and least privilege assignment."),
    ("remote-work", "Remote Work Security Policy", "Remote users must use managed devices, VPN for internal systems, MFA, and secure network practices."),
    ("data-quality", "Data Quality Policy", "Critical datasets require freshness, completeness, schema, and uniqueness checks with owner-reviewed exceptions."),
]


def make_document(
    document_id: str,
    title: str,
    category: str,
    department: str,
    source_type: str,
    tags: list[str],
    content: str,
    index: int,
    access_level: str = "internal",
) -> dict:
    return {
        "document_id": document_id,
        "title": title,
        "category": category,
        "department": department,
        "source_type": source_type,
        "created_at": f"2026-02-{(index % 27) + 1:02d}",
        "version": "1.0",
        "access_level": access_level,
        "tags": tags,
        "content": content,
        "expected_questions": [
            f"What caused {title.lower()}?",
            f"How should support resolve {title.lower()}?",
        ],
        "expected_answer_sources": ["symptoms", "root cause", "resolution", "escalation"],
    }


def generate_tickets() -> list[dict]:
    documents: list[dict] = []
    for topic_index, topic in enumerate(TOPICS):
        for variant in range(6):
            priority = ["P3", "P2", "P3", "P1", "P2", "P4"][variant]
            content = (
                f"Ticket summary: {topic['symptom']} in environment {variant + 1}. "
                f"User impact: affected users cannot complete the normal workflow until support acts. "
                f"Priority: {priority}. Troubleshooting already attempted: verify account state, "
                f"review recent changes, inspect logs, and reproduce from a controlled test device. "
                f"Root cause: {topic['root_cause']}. Resolution: {topic['resolution']}. "
                f"Validation: confirm the user can complete the workflow and record the ticket evidence. "
                f"Escalation path: {topic['escalation']} if the issue repeats after the documented fix."
            )
            documents.append(
                make_document(
                    document_id=f"ticket-{topic['key']}-{variant + 1:03d}",
                    title=f"{topic['title']} #{variant + 1}",
                    category=topic["category"],
                    department=topic["department"],
                    source_type="ticket",
                    tags=topic["tags"],
                    content=content,
                    index=len(documents),
                )
            )
    return documents


def generate_runbooks(start_index: int) -> list[dict]:
    documents: list[dict] = []
    for index, topic in enumerate(TOPICS):
        content = (
            f"Purpose: restore service for {topic['title'].lower()}. Scope: internal managed systems. "
            f"Prerequisites: support console access, recent logs, affected user or service identifier, "
            f"and permission to apply the standard fix. Procedure: confirm symptoms, check recent "
            f"changes, inspect logs, apply this resolution: {topic['resolution']}. Validation: verify "
            f"that the original symptom is gone and record evidence. Rollback: revert only the changed "
            f"configuration or token when validation fails. Escalation: contact {topic['escalation']} "
            f"when the procedure does not restore service."
        )
        documents.append(
            make_document(
                document_id=f"runbook-{topic['key']}-001",
                title=f"{topic['title']} Runbook",
                category=topic["category"],
                department=topic["department"],
                source_type="runbook",
                tags=topic["tags"],
                content=content,
                index=start_index + index,
                access_level="restricted" if topic["key"] == "cve-patching" else "internal",
            )
        )
    return documents


def generate_policies(start_index: int) -> list[dict]:
    documents: list[dict] = []
    for index, (key, title, rule) in enumerate(POLICIES):
        content = (
            f"Objective: define enterprise requirements for {title.lower()}. Scope: employees, "
            f"contractors, services, and managed systems. Rules: {rule} Responsibilities: owners "
            f"must maintain evidence, managers approve exceptions, and operations teams monitor "
            f"compliance. Exceptions: document business justification, owner approval, expiry date, "
            f"and compensating control. Review cycle: quarterly for high-risk controls and annually "
            f"for standard controls. Consequences: unresolved violations are escalated to leadership."
        )
        documents.append(
            make_document(
                document_id=f"policy-{key}-001",
                title=title,
                category="security_policy" if "Access" in title or "Security" in title else "data_policy",
                department="security" if "Access" in title or "Security" in title else "data_platform",
                source_type="policy",
                tags=[key, "policy"],
                content=content,
                index=start_index + index,
                access_level="internal",
            )
        )
    return documents


def generate_incidents(start_index: int) -> list[dict]:
    documents: list[dict] = []
    for index, topic in enumerate(TOPICS):
        content = (
            f"Summary: {topic['title'].lower()} caused operational impact for a subset of users. "
            f"Timeline: detection at 09:{index:02d}, mitigation at 09:{index + 20:02d}, validation "
            f"at 10:{index:02d}. Affected systems: {', '.join(topic['tags'])}. Severity: SEV{2 if index % 3 == 0 else 3}. "
            f"Detection method: alert, ticket spike, or dashboard anomaly. Root cause: {topic['root_cause']}. "
            f"Mitigation: {topic['resolution']}. Permanent fix: add validation, monitoring, and owner review. "
            f"Prevention actions: update runbook, add pre-change checks, and review similar services."
        )
        documents.append(
            make_document(
                document_id=f"incident-{topic['key']}-001",
                title=f"{topic['title']} Incident Report",
                category="incident",
                department=topic["department"],
                source_type="incident_report",
                tags=topic["tags"] + ["incident"],
                content=content,
                index=start_index + index,
            )
        )
    return documents


def generate_wiki_adr_faq(start_index: int) -> list[dict]:
    docs: list[dict] = []
    for index, topic in enumerate(TOPICS):
        wiki_content = (
            f"Overview: this page helps new team members understand {topic['title'].lower()}. "
            f"Common owner team: {topic['escalation']}. Normal workflow: identify symptoms, "
            f"check documentation, follow the runbook, validate the fix, and record evidence. "
            f"Limitations: do not invent approvals, credentials, or system state."
        )
        docs.append(
            make_document(
                document_id=f"wiki-{topic['key']}-001",
                title=f"{topic['title']} Team Wiki",
                category="wiki",
                department=topic["department"],
                source_type="wiki",
                tags=topic["tags"] + ["wiki"],
                content=wiki_content,
                index=start_index + len(docs),
            )
        )

    adr_topics = [
        ("pgvector", "Use PostgreSQL and pgvector for MVP Retrieval", "PostgreSQL plus pgvector keeps metadata, logs, evaluation records, and embeddings in one local database."),
        ("fastapi", "Use FastAPI for Backend API", "FastAPI provides typed request schemas, generated OpenAPI docs, and simple local development."),
        ("streamlit", "Use Streamlit for MVP Chat UI", "Streamlit lets the project show chat, citations, confidence, and source excerpts quickly."),
        ("hybrid-search", "Add Hybrid Search After Vector Baseline", "Hybrid search combines semantic similarity and exact keyword matching for operational terms."),
        ("evaluation", "Build Evaluation Before Advanced Modes", "Evaluation makes retrieval quality and hallucination risk visible before adding agentic features."),
    ]
    for key, title, decision in adr_topics:
        content = (
            f"Status: accepted. Context: the project needs a professional RAG implementation "
            f"that is explainable and practical on a laptop. Decision: {decision} Options "
            f"considered: separate vector database, managed search service, or custom file index. "
            f"Consequences: the implementation remains simple for demo use while leaving room "
            f"for later scale and production hardening."
        )
        docs.append(
            make_document(
                document_id=f"adr-{key}-001",
                title=f"ADR: {title}",
                category="architecture",
                department="data_platform",
                source_type="adr",
                tags=[key, "architecture"],
                content=content,
                index=start_index + len(docs),
            )
        )

    for index, topic in enumerate(TOPICS):
        content = (
            f"Q: What is the first check for {topic['title'].lower()}? A: Confirm the symptom, "
            f"recent changes, logs, and ownership. Q: What is the likely root cause? A: {topic['root_cause']}. "
            f"Q: What is the standard resolution? A: {topic['resolution']}. Q: When should support "
            f"escalate? A: Escalate to {topic['escalation']} when the documented fix does not work."
        )
        docs.append(
            make_document(
                document_id=f"faq-{topic['key']}-001",
                title=f"{topic['title']} FAQ",
                category="faq",
                department=topic["department"],
                source_type="faq",
                tags=topic["tags"] + ["faq"],
                content=content,
                index=start_index + len(docs),
            )
        )
    return docs


def generate_documents() -> list[dict]:
    documents = generate_tickets()
    documents.extend(generate_runbooks(len(documents)))
    documents.extend(generate_policies(len(documents)))
    documents.extend(generate_incidents(len(documents)))
    documents.extend(generate_wiki_adr_faq(len(documents)))
    return documents


def write_jsonl(documents: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for document in documents:
            handle.write(json.dumps(document, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic enterprise RAG documents.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    documents = generate_documents()
    write_jsonl(documents, args.output)
    print(f"Wrote {len(documents)} documents to {args.output}")


if __name__ == "__main__":
    main()

