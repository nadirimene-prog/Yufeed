"""
Seed Monitoring Rules
Creates pre-built monitoring rules based on common AML/CFT regulations.

This demonstrates Yufeed's innovation: rules derived from actual regulations.
"""
import sys
import os
from decimal import Decimal
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import SessionLocal
from src.models.transaction_models import MonitoringRule
from src.services.rules_engine import RuleBuilder

def seed_rules():
    """Create pre-built monitoring rules."""
    db = SessionLocal()

    try:
        print("Seeding monitoring rules...")

        rules_data = []

        # ====================================================================
        # 1. AMOUNT-BASED RULES (EU Anti-Money Laundering Directives)
        # ====================================================================

        # EU AML Directive: Transactions over €10,000
        rules_data.append({
            "rule_id": f"RULE-AML-{uuid.uuid4().hex[:8].upper()}",
            "name": "Large Transaction - Over €10,000",
            "description": "Transactions exceeding €10,000 require enhanced due diligence under EU AML Directive",
            "category": "amount_threshold",
            "severity": "medium",
            "conditions": {
                "conditions": [
                    {"field": "amount", "operator": "greater_than", "value": 10000},
                    {"field": "currency", "operator": "equals", "value": "EUR"}
                ],
                "logic": "AND"
            },
            "regulation_article": "Article 13",
            "regulatory_requirement": "Enhanced customer due diligence for transactions over €10,000",
            "enabled": True
        })

        # Very Large Transaction - Over €50,000
        rules_data.append({
            "rule_id": f"RULE-AML-{uuid.uuid4().hex[:8].upper()}",
            "name": "Very Large Transaction - Over €50,000",
            "description": "High-value transactions requiring immediate review",
            "category": "amount_threshold",
            "severity": "high",
            "conditions": {
                "conditions": [
                    {"field": "amount", "operator": "greater_than", "value": 50000},
                    {"field": "currency", "operator": "equals", "value": "EUR"}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "High-value transaction monitoring",
            "enabled": True
        })

        # Critical Transaction - Over €100,000
        rules_data.append({
            "rule_id": f"RULE-AML-{uuid.uuid4().hex[:8].upper()}",
            "name": "Critical Transaction - Over €100,000",
            "description": "Critical high-value transaction requiring immediate escalation",
            "category": "amount_threshold",
            "severity": "critical",
            "conditions": {
                "conditions": [
                    {"field": "amount", "operator": "greater_than", "value": 100000},
                    {"field": "currency", "operator": "equals", "value": "EUR"}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "Critical transaction monitoring and reporting",
            "enabled": True
        })

        # ====================================================================
        # 2. STRUCTURING DETECTION
        # ====================================================================

        # Just-Below-Threshold Transactions (Structuring Indicator)
        rules_data.append({
            "rule_id": f"RULE-STRUCT-{uuid.uuid4().hex[:8].upper()}",
            "name": "Potential Structuring - Just Below €10,000",
            "description": "Transaction amount just below reporting threshold (potential structuring)",
            "category": "structuring",
            "severity": "high",
            "conditions": {
                "conditions": [
                    {"field": "amount", "operator": "greater_than_or_equal", "value": 9000},
                    {"field": "amount", "operator": "less_than", "value": 10000},
                    {"field": "currency", "operator": "equals", "value": "EUR"}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "Anti-structuring monitoring to detect attempts to evade reporting thresholds",
            "enabled": True
        })

        # ====================================================================
        # 3. SANCTIONS & HIGH-RISK JURISDICTIONS
        # ====================================================================

        # OFAC/EU Sanctioned Countries
        sanctioned_countries = ['KP', 'IR', 'SY', 'CU', 'VE']
        rules_data.append({
            "rule_id": f"RULE-SANC-{uuid.uuid4().hex[:8].upper()}",
            "name": "Sanctioned Jurisdiction Transaction",
            "description": "Transaction involving OFAC/EU sanctioned countries",
            "category": "sanctions",
            "severity": "critical",
            "conditions": {
                "conditions": [
                    {"field": "country_code", "operator": "in", "value": sanctioned_countries}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "OFAC and EU sanctions compliance - transactions with sanctioned jurisdictions",
            "enabled": True
        })

        # High-Risk Jurisdictions (FATF Grey List)
        high_risk_countries = ['MM', 'AF', 'YE', 'IQ', 'LY', 'SO', 'SD']
        rules_data.append({
            "rule_id": f"RULE-RISK-{uuid.uuid4().hex[:8].upper()}",
            "name": "High-Risk Jurisdiction Transaction",
            "description": "Transaction involving FATF high-risk jurisdiction",
            "category": "high_risk_geography",
            "severity": "high",
            "conditions": {
                "conditions": [
                    {"field": "country_code", "operator": "in", "value": high_risk_countries}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "FATF recommendations - enhanced due diligence for high-risk jurisdictions",
            "enabled": True
        })

        # ====================================================================
        # 4. VELOCITY RULES
        # ====================================================================

        # High Frequency - Many Transactions in Short Time
        rules_data.append({
            "rule_id": f"RULE-VEL-{uuid.uuid4().hex[:8].upper()}",
            "name": "High Transaction Frequency",
            "description": "More than 10 transactions in 24 hours",
            "category": "velocity",
            "severity": "medium",
            "conditions": {
                "conditions": [],
                "logic": "AND"
            },
            "thresholds": {
                "transaction_count": 10,
                "time_window_hours": 24
            },
            "regulatory_requirement": "Transaction velocity monitoring for unusual patterns",
            "enabled": True
        })

        # Very High Frequency
        rules_data.append({
            "rule_id": f"RULE-VEL-{uuid.uuid4().hex[:8].upper()}",
            "name": "Very High Transaction Frequency",
            "description": "More than 20 transactions in 24 hours - potential automated activity",
            "category": "velocity",
            "severity": "high",
            "conditions": {
                "conditions": [],
                "logic": "AND"
            },
            "thresholds": {
                "transaction_count": 20,
                "time_window_hours": 24
            },
            "regulatory_requirement": "Automated transaction monitoring",
            "enabled": True
        })

        # High Volume in Short Time
        rules_data.append({
            "rule_id": f"RULE-VEL-{uuid.uuid4().hex[:8].upper()}",
            "name": "High Volume - Over €100,000 in 24h",
            "description": "Total transaction volume exceeds €100,000 in 24 hours",
            "category": "velocity",
            "severity": "high",
            "conditions": {
                "conditions": [],
                "logic": "AND"
            },
            "thresholds": {
                "total_amount": 100000,
                "time_window_hours": 24
            },
            "regulatory_requirement": "High-volume transaction monitoring",
            "enabled": True
        })

        # ====================================================================
        # 5. TRANSACTION TYPE RULES
        # ====================================================================

        # Large Cash Withdrawal
        rules_data.append({
            "rule_id": f"RULE-CASH-{uuid.uuid4().hex[:8].upper()}",
            "name": "Large Cash Withdrawal",
            "description": "Cash withdrawal over €5,000",
            "category": "cash_transaction",
            "severity": "medium",
            "conditions": {
                "conditions": [
                    {"field": "transaction_type", "operator": "equals", "value": "withdrawal"},
                    {"field": "amount", "operator": "greater_than", "value": 5000}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "Cash transaction monitoring",
            "enabled": True
        })

        # Large Wire Transfer
        rules_data.append({
            "rule_id": f"RULE-WIRE-{uuid.uuid4().hex[:8].upper()}",
            "name": "Large Wire Transfer",
            "description": "International wire transfer over €15,000",
            "category": "wire_transfer",
            "severity": "medium",
            "conditions": {
                "conditions": [
                    {"field": "transaction_type", "operator": "equals", "value": "wire_transfer"},
                    {"field": "amount", "operator": "greater_than", "value": 15000}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "Wire transfer monitoring under Travel Rule",
            "enabled": True
        })

        # ====================================================================
        # 6. ROUND AMOUNT RULES (Money Laundering Indicator)
        # ====================================================================

        # Large Round Amount
        rules_data.append({
            "rule_id": f"RULE-ROUND-{uuid.uuid4().hex[:8].upper()}",
            "name": "Large Round Amount Transaction",
            "description": "Large transaction with round amount (potential money laundering indicator)",
            "category": "unusual_pattern",
            "severity": "low",
            "conditions": {
                "conditions": [
                    {"field": "amount", "operator": "greater_than", "value": 10000}
                ],
                "logic": "AND"
            },
            "regulatory_requirement": "Unusual pattern detection",
            "enabled": True
        })

        # ====================================================================
        # 7. POLITICALLY EXPOSED PERSONS (PEP) - Placeholder
        # ====================================================================

        # Note: This would require integration with PEP databases
        # For now, using enhanced_due_diligence flag as proxy

        # ====================================================================
        # Insert rules into database
        # ====================================================================

        created_count = 0
        for rule_data in rules_data:
            # Check if rule already exists
            existing = db.query(MonitoringRule).filter(
                MonitoringRule.rule_id == rule_data["rule_id"]
            ).first()

            if existing:
                print(f"  ⏭️  Rule {rule_data['name']} already exists, skipping")
                continue

            rule = MonitoringRule(**rule_data)
            db.add(rule)
            created_count += 1
            print(f"  ✅ Created rule: {rule_data['name']} ({rule_data['severity']})")

        db.commit()

        print(f"\n✅ Successfully created {created_count} monitoring rules")
        print(f"📊 Total rules in database: {db.query(MonitoringRule).count()}")

        # Print summary by category
        print("\n📋 Rules by Category:")
        from sqlalchemy import func
        categories = db.query(
            MonitoringRule.category,
            func.count(MonitoringRule.id).label('count')
        ).group_by(MonitoringRule.category).all()

        for category, count in categories:
            print(f"   {category or 'uncategorized'}: {count} rules")

    except Exception as e:
        print(f"❌ Error seeding rules: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_rules()
