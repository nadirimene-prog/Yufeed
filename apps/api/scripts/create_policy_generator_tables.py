#!/usr/bin/env python3
"""
Database Migration: Smart Policy Generator
Tables for AI-generated policies and generation jobs
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_database_url():
    possible_dbs = ["./compliance.db", "./src/compliance.db"]
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            return f"sqlite:///{db_path}"
    return "sqlite:///./compliance.db"


import os

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)


def run_migration():
    print("\n" + "=" * 70)
    print("SMART POLICY GENERATOR - DATABASE MIGRATION")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")

    with engine.connect() as conn:
        # 1. Create policy_generation_jobs table
        print("\n1. Creating policy_generation_jobs table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS policy_generation_jobs (
                    id INTEGER PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL UNIQUE,
                    template_id VARCHAR(100) NOT NULL,
                    base_policy_id INTEGER,
                    status VARCHAR(50) DEFAULT 'pending',
                    obligations_json TEXT NOT NULL,
                    generated_content TEXT,
                    generated_summary TEXT,
                    ai_confidence FLOAT,
                    ai_model VARCHAR(50),
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    reviewed_by INTEGER,
                    reviewed_at TIMESTAMP,
                    review_notes TEXT,
                    final_policy_id INTEGER
                )
            """
                )
            )
            print("   ✅ policy_generation_jobs created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 2. Create policy_template_variables table
        print("\n2. Creating policy_template_variables table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS policy_template_variables (
                    id INTEGER PRIMARY KEY,
                    template_id VARCHAR(100) NOT NULL,
                    variable_name VARCHAR(100) NOT NULL,
                    variable_type VARCHAR(50) DEFAULT 'text',
                    description TEXT,
                    default_value TEXT,
                    is_required BOOLEAN DEFAULT 1,
                    placeholder TEXT,
                    example_value TEXT,
                    ai_prompt_hint TEXT,
                    UNIQUE(template_id, variable_name)
                )
            """
                )
            )
            print("   ✅ policy_template_variables created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 3. Create policy_draft_versions table
        print("\n3. Creating policy_draft_versions table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS policy_draft_versions (
                    id INTEGER PRIMARY KEY,
                    generation_job_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    changes_summary TEXT,
                    ai_feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50) DEFAULT 'ai',
                    UNIQUE(generation_job_id, version_number)
                )
            """
                )
            )
            print("   ✅ policy_draft_versions created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 4. Create policy_section_templates table
        print("\n4. Creating policy_section_templates table...")
        try:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS policy_section_templates (
                    id INTEGER PRIMARY KEY,
                    template_id VARCHAR(100) NOT NULL,
                    section_name VARCHAR(100) NOT NULL,
                    section_order INTEGER NOT NULL,
                    title_template VARCHAR(255),
                    content_template TEXT,
                    ai_instructions TEXT,
                    is_required BOOLEAN DEFAULT 1,
                    depends_on_obligations BOOLEAN DEFAULT 0
                )
            """
                )
            )
            print("   ✅ policy_section_templates created")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 5. Add columns to policy_documents
        print("\n5. Adding generation columns to policy_documents...")
        columns = [
            ("generation_job_id", "INTEGER"),
            ("is_ai_generated", "BOOLEAN DEFAULT 0"),
            ("ai_confidence_score", "FLOAT"),
            ("generation_metadata", "JSON"),
        ]

        for col_name, col_type in columns:
            try:
                conn.execute(
                    text(
                        f"""
                    ALTER TABLE policy_documents
                    ADD COLUMN {col_name} {col_type}
                """
                    )
                )
                print(f"   ✅ Added {col_name}")
            except Exception as e:
                print(f"   ⚠️  {col_name}: {e}")

        # 6. Add generation tracking to regulatory_obligations
        print("\n6. Adding generation tracking columns...")
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE regulatory_obligations
                ADD COLUMN generated_policy_id INTEGER
            """
                )
            )
            print("   ✅ Added generated_policy_id")
        except Exception as e:
            print(f"   ⚠️  {e}")

        # 7. Create indexes
        print("\n7. Creating indexes...")
        indexes = [
            ("idx_gen_jobs_status", "policy_generation_jobs", "status"),
            ("idx_gen_jobs_template", "policy_generation_jobs", "template_id"),
            ("idx_gen_jobs_created", "policy_generation_jobs", "created_by"),
            ("idx_template_vars_template", "policy_template_variables", "template_id"),
            ("idx_draft_versions_job", "policy_draft_versions", "generation_job_id"),
            ("idx_section_templates_template", "policy_section_templates", "template_id"),
        ]

        for idx_name, table, column in indexes:
            try:
                conn.execute(
                    text(
                        f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})
                """
                    )
                )
                print(f"   ✅ {idx_name}")
            except Exception as e:
                print(f"   ⚠️  {idx_name}: {e}")

        # 8. Populate template variables for existing templates
        print("\n8. Populating template variables...")
        populate_template_variables(conn)

        # 9. Populate section templates
        print("\n9. Populating section templates...")
        populate_section_templates(conn)

        conn.commit()

    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)


def populate_template_variables(conn):
    """Populate template variables for AML/CFT templates."""
    variables = [
        # AML-CFT Policy Master
        (
            "aml-cft-policy-master",
            "institution_name",
            "text",
            "Name of the financial institution",
            None,
            1,
            "[Your Institution Name]",
            "Acme Bank",
            "The official registered name of the institution",
        ),
        (
            "aml-cft-policy-master",
            "jurisdiction",
            "text",
            "Primary regulatory jurisdiction",
            None,
            1,
            "[Jurisdiction]",
            "European Union",
            "The main jurisdiction where the institution operates",
        ),
        (
            "aml-cft-policy-master",
            "mlro_name",
            "text",
            "Name of the MLRO",
            None,
            1,
            "[MLRO Name]",
            "Jane Smith",
            "The name of the Money Laundering Reporting Officer",
        ),
        (
            "aml-cft-policy-master",
            "mlro_email",
            "email",
            "Email of the MLRO",
            None,
            1,
            "[MLRO Email]",
            "mlro@institution.com",
            "Contact email for the MLRO",
        ),
        (
            "aml-cft-policy-master",
            "risk_appetite",
            "select",
            "Risk appetite level",
            "medium",
            1,
            "[Risk Level]",
            "medium",
            "The institution's risk appetite: low, medium, or high",
        ),
        # Customer Due Diligence
        (
            "customer-due-diligence-policy",
            "cdd_threshold",
            "number",
            "CDD trigger threshold in EUR",
            "15000",
            1,
            "[Amount]",
            "15000",
            "Monetary threshold that triggers enhanced CDD",
        ),
        (
            "customer-due-diligence-policy",
            "simplified_cdd_allowed",
            "boolean",
            "Whether simplified CDD is permitted",
            "false",
            1,
            "[Yes/No]",
            "No",
            "Whether simplified CDD procedures are allowed for low-risk customers",
        ),
        (
            "customer-due-diligence-policy",
            "ongoing_monitoring_frequency",
            "select",
            "Frequency of ongoing monitoring",
            "annual",
            1,
            "[Frequency]",
            "Annual",
            "How often customer information is reviewed: quarterly, annual, biennial",
        ),
        # Enhanced Due Diligence
        (
            "enhanced-due-diligence-policy",
            "pep_threshold",
            "text",
            "Definition of PEP relationship",
            "immediate_family",
            1,
            "[Definition]",
            "Immediate family members and close associates",
            "How PEP relationships are defined",
        ),
        (
            "enhanced-due-diligence-policy",
            "high_risk_countries",
            "text",
            "List of high-risk jurisdictions",
            None,
            0,
            "[Country List]",
            "Countries on FATF grey list",
            "Jurisdictions requiring enhanced scrutiny",
        ),
        # Sanctions Screening
        (
            "sanctions-screening-policy",
            "screening_system",
            "text",
            "Name of screening system",
            None,
            1,
            "[System Name]",
            "Refinitiv World-Check",
            "The sanctions screening software used",
        ),
        (
            "sanctions-screening-policy",
            "real_time_screening",
            "boolean",
            "Real-time screening enabled",
            "true",
            1,
            "[Yes/No]",
            "Yes",
            "Whether transactions are screened in real-time",
        ),
        (
            "sanctions-screening-policy",
            "false_positive_threshold",
            "number",
            "False positive tolerance",
            "85",
            1,
            "[Percentage]",
            "85",
            "Match score threshold for automatic escalation",
        ),
        # STR Reporting
        (
            "suspicious-transaction-reporting",
            "str_deadline_hours",
            "number",
            "Hours to file STR",
            "24",
            1,
            "[Hours]",
            "24",
            "Maximum hours to file STR after detection",
        ),
        (
            "suspicious-transaction-reporting",
            "str_authority",
            "text",
            "STR filing authority",
            None,
            1,
            "[Authority]",
            "FIU (Financial Intelligence Unit)",
            "The authority to which STRs are filed",
        ),
        (
            "suspicious-transaction-reporting",
            "internal_escalation_hours",
            "number",
            "Internal escalation hours",
            "4",
            1,
            "[Hours]",
            "4",
            "Hours to escalate internally before filing",
        ),
    ]

    for var in variables:
        try:
            conn.execute(
                text(
                    """
                INSERT OR IGNORE INTO policy_template_variables
                (template_id, variable_name, variable_type, description, default_value, is_required, placeholder, example_value, ai_prompt_hint)
                VALUES (:template_id, :var_name, :var_type, :desc, :default, :required, :placeholder, :example, :hint)
            """
                ),
                {
                    "template_id": var[0],
                    "var_name": var[1],
                    "var_type": var[2],
                    "desc": var[3],
                    "default": var[4],
                    "required": var[5],
                    "placeholder": var[6],
                    "example": var[7],
                    "hint": var[8],
                },
            )
        except Exception as e:
            print(f"   Warning: Could not add variable {var[1]}: {e}")

    print(f"   Added {len(variables)} template variables")


def populate_section_templates(conn):
    """Populate section templates for common policy structure."""
    sections = [
        # AML-CFT Policy Master sections
        (
            "aml-cft-policy-master",
            1,
            "1. Purpose and Scope",
            "policy_purpose",
            "Define the purpose of this {policy_name} and its scope of application within {institution_name}.",
            "Explain why this policy exists and what areas it covers",
        ),
        (
            "aml-cft-policy-master",
            2,
            "2. Legal and Regulatory Basis",
            "regulatory_basis",
            "List the applicable laws, regulations, and guidelines including {regulatory_references}.",
            "Cite all relevant regulations with specific articles",
        ),
        (
            "aml-cft-policy-master",
            3,
            "3. Definitions",
            "definitions",
            "Define key terms including: {key_terms}",
            "Provide clear definitions for technical terms",
        ),
        (
            "aml-cft-policy-master",
            4,
            "4. Roles and Responsibilities",
            "roles",
            "Detail responsibilities of {mlro_name}, compliance team, and staff.",
            "Define who does what with specific responsibilities",
        ),
        (
            "aml-cft-policy-master",
            5,
            "5. Procedures",
            "procedures",
            "Step-by-step procedures derived from obligations: {obligation_procedures}",
            "Convert obligations into actionable procedures",
        ),
        (
            "aml-cft-policy-master",
            6,
            "6. Risk Assessment",
            "risk_assessment",
            "Risk factors and assessment methodology for {risk_categories}.",
            "Describe risk assessment process",
        ),
        (
            "aml-cft-policy-master",
            7,
            "7. Record Keeping",
            "record_keeping",
            "Data retention requirements: {retention_periods}.",
            "Specify what records to keep and for how long",
        ),
        (
            "aml-cft-policy-master",
            8,
            "8. Training Requirements",
            "training",
            "Training frequency and content for {target_audience}.",
            "Define who needs training and on what schedule",
        ),
        (
            "aml-cft-policy-master",
            9,
            "9. Monitoring and Review",
            "monitoring",
            "Policy review schedule and compliance monitoring.",
            "How the policy will be monitored and updated",
        ),
        (
            "aml-cft-policy-master",
            10,
            "10. References",
            "references",
            "Related policies and external documents.",
            "List related internal and external documents",
        ),
    ]

    for section in sections:
        try:
            conn.execute(
                text(
                    """
                INSERT OR IGNORE INTO policy_section_templates
                (template_id, section_name, section_order, title_template, ai_instructions, is_required, depends_on_obligations)
                VALUES (:template_id, :section_name, :order, :title, :instructions, 1, :depends)
            """
                ),
                {
                    "template_id": section[0],
                    "section_name": section[2],
                    "order": section[1],
                    "title": section[3],
                    "instructions": section[5],
                    "depends": 1 if "obligation" in section[4].lower() else 0,
                },
            )
        except Exception as e:
            print(f"   Warning: Could not add section {section[2]}: {e}")

    print(f"   Added {len(sections)} section templates")


if __name__ == "__main__":
    run_migration()
