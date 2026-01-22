"""
Generate Sample Transaction Data
Creates realistic test data for transaction monitoring system.
"""
import sys
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import SessionLocal
from src.models.transaction_models import Transaction
from src.services.rules_engine import RulesEngine
from src.services.risk_scoring import RiskScoringService

# Sample data
CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF']
TRANSACTION_TYPES = ['deposit', 'withdrawal', 'transfer', 'wire_transfer', 'payment']
COUNTRIES = ['FR', 'DE', 'IT', 'ES', 'NL', 'BE', 'CH', 'AT', 'PL', 'SE', 'NO', 'DK']
HIGH_RISK_COUNTRIES = ['IR', 'KP', 'SY', 'MM', 'AF']

# User pools
NORMAL_USERS = [f"USER{i:04d}" for i in range(1, 51)]  # 50 normal users
HIGH_RISK_USERS = [f"RISK{i:04d}" for i in range(1, 11)]  # 10 high-risk users
FRAUD_RING_USERS = [f"FRAUD{i:04d}" for i in range(1, 6)]  # 5 fraud ring members


def generate_normal_transaction(user_id: str, tx_count: int) -> dict:
    """Generate a normal, low-risk transaction."""
    amount = random.uniform(10, 5000)

    return {
        "transaction_id": f"TX-NORM-{tx_count:08d}",
        "user_id": user_id,
        "amount": Decimal(str(round(amount, 2))),
        "currency": random.choice(['EUR', 'USD', 'GBP']),
        "transaction_type": random.choice(['deposit', 'payment', 'transfer']),
        "counterparty_id": random.choice(NORMAL_USERS),
        "timestamp": datetime.utcnow() - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        ),
        "country_code": random.choice(COUNTRIES),
        "ip_address": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "status": 'completed'
    }


def generate_high_value_transaction(user_id: str, tx_count: int) -> dict:
    """Generate high-value transaction (should trigger amount rules)."""
    amount = random.uniform(10000, 100000)

    return {
        "transaction_id": f"TX-HIGH-{tx_count:08d}",
        "user_id": user_id,
        "amount": Decimal(str(round(amount, 2))),
        "currency": 'EUR',
        "transaction_type": random.choice(['wire_transfer', 'transfer']),
        "counterparty_id": random.choice(NORMAL_USERS + HIGH_RISK_USERS),
        "timestamp": datetime.utcnow() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23)
        ),
        "country_code": random.choice(COUNTRIES),
        "ip_address": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "status": 'completed'
    }


def generate_structuring_transaction(user_id: str, tx_count: int) -> dict:
    """Generate structuring transaction (just below €10K threshold)."""
    amount = random.uniform(9000, 9999)

    return {
        "transaction_id": f"TX-STRUCT-{tx_count:08d}",
        "user_id": user_id,
        "amount": Decimal(str(round(amount, 2))),
        "currency": 'EUR',
        "transaction_type": 'withdrawal',
        "counterparty_id": None,
        "timestamp": datetime.utcnow() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23)
        ),
        "country_code": 'FR',
        "ip_address": f"172.16.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "status": 'completed'
    }


def generate_sanctions_transaction(user_id: str, tx_count: int) -> dict:
    """Generate transaction with sanctioned country."""
    amount = random.uniform(1000, 50000)

    return {
        "transaction_id": f"TX-SANC-{tx_count:08d}",
        "user_id": user_id,
        "amount": Decimal(str(round(amount, 2))),
        "currency": 'USD',
        "transaction_type": 'wire_transfer',
        "counterparty_id": f"SANC{random.randint(1, 10):04d}",
        "timestamp": datetime.utcnow() - timedelta(
            days=random.randint(0, 30)
        ),
        "country_code": random.choice(HIGH_RISK_COUNTRIES),
        "ip_address": f"185.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "status": 'completed'
    }


def generate_fraud_ring_transaction(user_id: str, tx_count: int, counterparty_pool: list) -> dict:
    """Generate transaction within fraud ring (circular flows)."""
    amount = random.uniform(5000, 20000)

    return {
        "transaction_id": f"TX-FRAUD-{tx_count:08d}",
        "user_id": user_id,
        "amount": Decimal(str(round(amount, 2))),
        "currency": 'EUR',
        "transaction_type": 'transfer',
        "counterparty_id": random.choice([u for u in counterparty_pool if u != user_id]),
        "timestamp": datetime.utcnow() - timedelta(
            days=random.randint(0, 60),
            hours=random.randint(0, 23)
        ),
        "country_code": random.choice(COUNTRIES),
        "ip_address": "10.20.30.40",  # Shared IP (suspicious!)
        "device_fingerprint": "DEVICE-FRAUD-001",  # Shared device
        "status": 'completed'
    }


def generate_velocity_pattern(user_id: str, start_count: int) -> list:
    """Generate velocity pattern (many transactions in short time)."""
    transactions = []
    base_time = datetime.utcnow() - timedelta(hours=random.randint(1, 12))

    for i in range(15):  # 15 transactions in short time
        transactions.append({
            "transaction_id": f"TX-VEL-{start_count + i:08d}",
            "user_id": user_id,
            "amount": Decimal(str(round(random.uniform(100, 1000), 2))),
            "currency": 'EUR',
            "transaction_type": 'transfer',
            "counterparty_id": random.choice(NORMAL_USERS),
            "timestamp": base_time + timedelta(minutes=i * 30),
            "country_code": 'DE',
            "ip_address": f"192.168.100.{random.randint(1, 255)}",
            "status": 'completed'
        })

    return transactions


def main():
    """Generate comprehensive test dataset."""
    db = SessionLocal()
    tx_count = 0

    print("Generating sample transaction data...\n")

    try:
        # 1. Normal transactions (bulk)
        print("1. Generating normal transactions...")
        normal_transactions = []
        for user in NORMAL_USERS:
            for _ in range(random.randint(5, 15)):
                tx = generate_normal_transaction(user, tx_count)
                normal_transactions.append(Transaction(**tx))
                tx_count += 1

        db.bulk_save_objects(normal_transactions)
        print(f"   ✅ Created {len(normal_transactions)} normal transactions")

        # 2. High-value transactions
        print("\n2. Generating high-value transactions...")
        high_value_txs = []
        for user in random.sample(NORMAL_USERS, 20):
            for _ in range(random.randint(1, 3)):
                tx = generate_high_value_transaction(user, tx_count)
                high_value_txs.append(Transaction(**tx))
                tx_count += 1

        db.bulk_save_objects(high_value_txs)
        print(f"   ✅ Created {len(high_value_txs)} high-value transactions")

        # 3. Structuring patterns
        print("\n3. Generating structuring patterns...")
        structuring_txs = []
        for user in random.sample(HIGH_RISK_USERS, 5):
            for _ in range(random.randint(3, 5)):
                tx = generate_structuring_transaction(user, tx_count)
                structuring_txs.append(Transaction(**tx))
                tx_count += 1

        db.bulk_save_objects(structuring_txs)
        print(f"   ✅ Created {len(structuring_txs)} structuring transactions")

        # 4. Sanctions violations
        print("\n4. Generating sanctions-related transactions...")
        sanctions_txs = []
        for user in random.sample(HIGH_RISK_USERS, 3):
            for _ in range(random.randint(1, 2)):
                tx = generate_sanctions_transaction(user, tx_count)
                sanctions_txs.append(Transaction(**tx))
                tx_count += 1

        db.bulk_save_objects(sanctions_txs)
        print(f"   ✅ Created {len(sanctions_txs)} sanctions transactions")

        # 5. Fraud ring network
        print("\n5. Generating fraud ring network...")
        fraud_ring_txs = []
        for user in FRAUD_RING_USERS:
            for _ in range(random.randint(5, 10)):
                tx = generate_fraud_ring_transaction(user, tx_count, FRAUD_RING_USERS)
                fraud_ring_txs.append(Transaction(**tx))
                tx_count += 1

        db.bulk_save_objects(fraud_ring_txs)
        print(f"   ✅ Created {len(fraud_ring_txs)} fraud ring transactions")

        # 6. Velocity patterns
        print("\n6. Generating velocity patterns...")
        velocity_txs = []
        for user in random.sample(HIGH_RISK_USERS, 3):
            pattern = generate_velocity_pattern(user, tx_count)
            for tx_data in pattern:
                velocity_txs.append(Transaction(**tx_data))
                tx_count += 1

        db.bulk_save_objects(velocity_txs)
        print(f"   ✅ Created {len(velocity_txs)} velocity transactions")

        db.commit()

        print(f"\n✅ Total transactions created: {tx_count}")
        print(f"\n📊 Dataset Summary:")
        print(f"   - Normal users: {len(NORMAL_USERS)}")
        print(f"   - High-risk users: {len(HIGH_RISK_USERS)}")
        print(f"   - Fraud ring members: {len(FRAUD_RING_USERS)}")
        print(f"   - Total transactions: {tx_count}")

        # Process some transactions to generate alerts
        print(f"\n🔄 Processing transactions to generate alerts...")
        print("   (Processing first 100 transactions)")

        risk_service = RiskScoringService(db)
        rules_engine = RulesEngine(db)

        processed = 0
        alerts_generated = 0

        for tx in db.query(Transaction).limit(100).all():
            try:
                # Score transaction
                risk_score = risk_service.score_transaction(tx.id)
                tx.risk_score = risk_score
                tx.risk_level = risk_service.get_risk_level(risk_score)

                # Evaluate rules
                alerts = rules_engine.evaluate_transaction(tx.id)
                alerts_generated += len(alerts)

                processed += 1

                if processed % 25 == 0:
                    print(f"   Processed {processed}/100 transactions...")

            except Exception as e:
                print(f"   ⚠️  Error processing transaction {tx.id}: {e}")

        db.commit()

        print(f"\n✅ Processed {processed} transactions")
        print(f"✅ Generated {alerts_generated} alerts")

        print(f"\n🎉 Sample data generation complete!")
        print(f"\nNext steps:")
        print(f"   1. View alerts: GET /api/alerts/")
        print(f"   2. View dashboard: GET /api/monitoring/dashboard")
        print(f"   3. Run AI triage: POST /api/ai/triage/batch")
        print(f"   4. Analyze networks: GET /api/network/analyze/FRAUD0001")

    except Exception as e:
        print(f"\n❌ Error generating data: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
