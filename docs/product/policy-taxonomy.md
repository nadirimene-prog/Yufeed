# EMI + CASP Policy Taxonomy

Reference for seeding standard policy templates required for Electronic Money Institution + Crypto-Asset Service Provider compliance.

## Policy Categories

### 1. AML/CFT Policies (AMLD5/6 + MiCA) - 9 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| AML/CFT Policy (Master) | AMLD5 Art. 8, MiCA Art. 68 |
| Customer Due Diligence (CDD) Policy | AMLD5 Art. 13-14 |
| Enhanced Due Diligence (EDD) Policy | AMLD5 Art. 18-24 |
| KYC/KYB Procedures | AMLD5 Art. 13 |
| Sanctions Screening Policy | EU Sanctions Regulations |
| PEP Identification & Monitoring | AMLD5 Art. 20-23 |
| Suspicious Transaction Reporting (STR) | AMLD5 Art. 33-34 |
| Travel Rule Compliance (crypto) | MiCA Art. 76, TFR |
| Record Keeping Policy | AMLD5 Art. 40 |

### 2. EMI-Specific Policies (EMD2 + PSD2) - 8 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| Safeguarding Policy | EMD2 Art. 7 |
| E-money Issuance & Redemption Policy | EMD2 Art. 11 |
| Payment Services Policy | PSD2 Art. 4 |
| Strong Customer Authentication (SCA) | PSD2 Art. 97, RTS |
| Fraud Prevention Policy | PSD2 Art. 96 |
| Complaint Handling Procedure | PSD2 Art. 101 |
| Outsourcing Policy | EBA Guidelines |
| Agent/Distributor Management | EMD2 Art. 3 |

### 3. CASP-Specific Policies (MiCA) - 8 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| Crypto-Asset Service Policy | MiCA Art. 59-64 |
| Custody & Safekeeping Policy | MiCA Art. 70 |
| Order Execution Policy | MiCA Art. 73 |
| Conflicts of Interest Policy | MiCA Art. 72 |
| Market Abuse Prevention | MiCA Art. 86-92 |
| White Paper Policy (if issuing) | MiCA Art. 4-14 |
| Token Listing/Delisting Policy | MiCA Art. 76 |
| Wallet Management Policy | MiCA Art. 70 |

### 4. Governance & Risk (Cross-cutting) - 8 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| Risk Management Framework | MiCA Art. 67, EBA GL |
| Internal Control Policy | EMD2, MiCA |
| Compliance Monitoring Policy | MiCA Art. 68 |
| Business Continuity Plan (BCP) | DORA Art. 11 |
| ICT Risk Management Policy | DORA Art. 5-14 |
| Incident Management Policy | DORA Art. 17, PSD2 Art. 96 |
| Outsourcing & Third-Party Risk | DORA Art. 28-30, EBA GL |
| Information Security Policy | DORA, GDPR |

### 5. Data Protection (GDPR) - 5 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| Data Protection Policy | GDPR Art. 24 |
| Data Retention Policy | GDPR Art. 5, AMLD5 Art. 40 |
| Data Subject Rights Procedure | GDPR Art. 12-23 |
| Data Breach Response Plan | GDPR Art. 33-34 |
| Privacy Notice | GDPR Art. 13-14 |

### 6. HR & Training - 4 Policies

| Policy | Regulatory Basis |
|--------|------------------|
| Fit & Proper Policy | MiCA Art. 62, EMD2 |
| Staff Training Policy (AML) | AMLD5 Art. 46 |
| Whistleblowing Policy | EU Whistleblower Directive |
| Remuneration Policy | MiCA Art. 66 |

---

## Policy Document Structure

Each policy should contain:

- **policy_id**: Unique identifier (kebab-case)
- **name**: Human-readable title
- **category**: One of: AML/CFT, EMI, CASP, Governance, GDPR, HR
- **version**: Semantic version (e.g., "1.0", "2.3")
- **status**: draft | in_review | approved | active | retired
- **owner**: Responsible executive (e.g., "MLRO", "CTO", "DPO")
- **regulatory_basis**: Array of regulatory articles (e.g., ["AMLD5 Art. 8", "MiCA Art. 68"])
- **effective_date**: When the policy becomes active
- **last_reviewed_at**: Most recent review date
- **review_frequency_months**: How often to review (typically 12)
- **source_url**: Link to external document (Notion, SharePoint, etc.)
- **content**: Full policy text or summary

---

## Workflow Integration

```
Regulatory Obligation Approved
  ↓
Check: Has linked_policy_id?
  ↓ NO
AI suggests matching policies based on:
  - Regulatory basis overlap
  - Keyword/semantic similarity
  - Scope tags
  ↓
Compliance Officer:
  [Select existing policy] OR [Create from template]
  ↓
Link obligation → policy
  ↓
Alert resolves
```

---

## Total: ~35-40 Policies Required

- 9 AML/CFT policies
- 8 EMI-specific policies  
- 8 CASP-specific policies
- 8 Governance/Risk policies
- 5 Data protection policies
- 4 HR policies
