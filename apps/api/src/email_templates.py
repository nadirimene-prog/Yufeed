"""
Email templates for Yufeed notifications.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

def get_email_header() -> str:
    """Common email header with styling."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale-1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
            }
            .content {
                background: #f9fafb;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }
            .document-card {
                background: white;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 15px 0;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .document-title {
                font-size: 18px;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 10px;
            }
            .document-meta {
                color: #6b7280;
                font-size: 14px;
                margin: 5px 0;
            }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 8px;
            }
            .badge-high {
                background: #fee2e2;
                color: #991b1b;
            }
            .badge-medium {
                background: #fef3c7;
                color: #92400e;
            }
            .badge-low {
                background: #d1fae5;
                color: #065f46;
            }
            .badge-domain {
                background: #e0e7ff;
                color: #3730a3;
            }
            .cta-button {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 20px;
            }
            .footer {
                text-align: center;
                color: #9ca3af;
                font-size: 12px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
            }
        </style>
    </head>
    <body>
    """

def get_email_footer() -> str:
    """Common email footer."""
    return """
        <div class="footer">
            <p>You received this email because you subscribed to Yufeed legal monitoring alerts.</p>
            <p>&copy; 2026 Yufeed | EU Legal Monitoring</p>
        </div>
    </body>
    </html>
    """

def daily_digest_template(documents: List[Dict[str, Any]], date: str = None) -> str:
    """Generate daily digest email HTML."""
    if date is None:
        date = utc_now().strftime("%B %d, %Y")

    html = get_email_header()
    html += f"""
    <div class="header">
        <h1>📜 Daily EU Legal Digest</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">{date}</p>
    </div>
    <div class="content">
        <h2 style="color: #1f2937; margin-top: 0;">New Documents & Updates</h2>
        <p>Here are the latest EU legal documents published today:</p>
    """

    if not documents:
        html += """
        <div class="document-card">
            <p style="color: #6b7280; margin: 0;">No new documents today.</p>
        </div>
        """
    else:
        for doc in documents:
            risk_badge = ""
            if doc.get("risk_level"):
                risk_class = f"badge-{doc['risk_level']}"
                risk_badge = f'<span class="badge {risk_class}">{doc["risk_level"].upper()} RISK</span>'

            domain_badge = ""
            if doc.get("compliance_domain"):
                domain_badge = f'<span class="badge badge-domain">{doc["compliance_domain"].upper()}</span>'

            html += f"""
            <div class="document-card">
                <div class="document-title">{doc.get('title', 'Untitled Document')}</div>
                <div class="document-meta">
                    <strong>CELEX:</strong> {doc.get('celex', 'N/A')}<br>
                    <strong>Type:</strong> {doc.get('type', 'Unknown')}
                </div>
                <div style="margin-top: 10px;">
                    {risk_badge}
                    {domain_badge}
                </div>
            </div>
            """

    html += """
        <a href="http://localhost:3000/dashboard" class="cta-button">View Full Dashboard</a>
    </div>
    """
    html += get_email_footer()
    return html

def watchlist_alert_template(watchlist_name: str, documents: List[Dict[str, Any]]) -> str:
    """Generate watchlist-specific alert email."""
    html = get_email_header()
    html += f"""
    <div class="header">
        <h1>🔔 Watchlist Alert</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">{watchlist_name}</p>
    </div>
    <div class="content">
        <h2 style="color: #1f2937; margin-top: 0;">New Matches Found</h2>
        <p>Your watchlist <strong>"{watchlist_name}"</strong> has {len(documents)} new matching document(s):</p>
    """

    for doc in documents:
        html += f"""
        <div class="document-card">
            <div class="document-title">{doc.get('title', 'Untitled Document')}</div>
            <div class="document-meta">
                <strong>CELEX:</strong> {doc.get('celex', 'N/A')}<br>
                <strong>Published:</strong> {doc.get('publication_date', 'Unknown')}
            </div>
        </div>
        """

    html += """
        <a href="http://localhost:3000/watchlists" class="cta-button">Manage Watchlists</a>
    </div>
    """
    html += get_email_footer()
    return html

def compliance_alert_template(high_risk_docs: List[Dict[str, Any]], upcoming_deadlines: List[Dict[str, Any]]) -> str:
    """Generate compliance-focused alert email."""
    html = get_email_header()
    html += """
    <div class="header">
        <h1>⚠️ Compliance Alert</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">High Priority Updates</p>
    </div>
    <div class="content">
    """

    if high_risk_docs:
        html += f"""
        <h2 style="color: #dc2626; margin-top: 0;">🚨 High Risk Documents ({len(high_risk_docs)})</h2>
        <p>These documents require immediate attention:</p>
        """

        for doc in high_risk_docs:
            html += f"""
            <div class="document-card" style="border-left-color: #dc2626;">
                <div class="document-title">{doc.get('title', 'Untitled')}</div>
                <div class="document-meta">
                    <strong>CELEX:</strong> {doc.get('celex', 'N/A')}<br>
                    <strong>Domain:</strong> {doc.get('compliance_domain', 'N/A').upper()}
                </div>
                <span class="badge badge-high">HIGH RISK</span>
            </div>
            """

    if upcoming_deadlines:
        html += f"""
        <h2 style="color: #ea580c; margin-top: 30px;">📅 Upcoming Deadlines ({len(upcoming_deadlines)})</h2>
        <p>Implementation deadlines in the next 30 days:</p>
        """

        for doc in upcoming_deadlines:
            deadline_date = doc.get('implementation_deadline', 'Unknown')
            if isinstance(deadline_date, datetime):
                deadline_date = deadline_date.strftime("%B %d, %Y")

            html += f"""
            <div class="document-card" style="border-left-color: #ea580c;">
                <div class="document-title">{doc.get('title', 'Untitled')}</div>
                <div class="document-meta">
                    <strong>Deadline:</strong> {deadline_date}<br>
                    <strong>CELEX:</strong> {doc.get('celex', 'N/A')}
                </div>
            </div>
            """

    html += """
        <a href="http://localhost:3000/dashboard" class="cta-button">View Compliance Dashboard</a>
    </div>
    """
    html += get_email_footer()
    return html

def test_email_template() -> str:
    """Generate test email for verification."""
    html = get_email_header()
    html += """
    <div class="header">
        <h1>✅ Test Email</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Email System Verification</p>
    </div>
    <div class="content">
        <h2 style="color: #1f2937; margin-top: 0;">Email Configuration Successful</h2>
        <p>If you're reading this, your Yufeed email system is properly configured and working!</p>
        <p style="margin-top: 20px;">You'll receive:</p>
        <ul style="color: #6b7280;">
            <li>Daily digest of new EU legal documents</li>
            <li>Watchlist alerts when matching documents are found</li>
            <li>Compliance alerts for high-risk documents and upcoming deadlines</li>
        </ul>
        <a href="http://localhost:3000" class="cta-button">Go to Yufeed</a>
    </div>
    """
    html += get_email_footer()
    return html
