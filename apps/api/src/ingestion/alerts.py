"""
Ingestion alerting service.
Sends email notifications on ingestion success/failure with detailed reports.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.email_service import send_email
from src.config import settings
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


@dataclass
class IngestionReport:
    """Summary of an ingestion run."""
    source_name: str
    status: str  # "completed", "failed", "partial"
    started_at: datetime
    completed_at: datetime
    items_seen: int
    items_new: int
    items_updated: int
    items_skipped: int
    errors: List[Dict[str, Any]]


def send_ingestion_report(
    reports: List[IngestionReport],
    to_email: Optional[str] = None,
) -> bool:
    """
    Send detailed ingestion report email.

    Args:
        reports: List of IngestionReport for each source
        to_email: Recipient email (defaults to ADMIN_EMAIL or EMAILS_FROM_EMAIL)
    """
    recipient = to_email or settings.ADMIN_EMAIL or settings.EMAILS_FROM_EMAIL

    # Calculate totals
    total_seen = sum(r.items_seen for r in reports)
    total_new = sum(r.items_new for r in reports)
    total_updated = sum(r.items_updated for r in reports)
    total_errors = sum(len(r.errors) for r in reports)

    # Determine overall status
    failed_sources = [r for r in reports if r.status == "failed"]
    partial_sources = [r for r in reports if r.status == "partial"]

    if failed_sources:
        overall_status = "FAILED"
        status_emoji = "🔴"
        subject = f"🔴 Yufeed Ingestion FAILED - {len(failed_sources)} source(s) with errors"
    elif partial_sources:
        overall_status = "PARTIAL"
        status_emoji = "🟡"
        subject = f"🟡 Yufeed Ingestion Partial - {total_errors} error(s)"
    else:
        overall_status = "SUCCESS"
        status_emoji = "🟢"
        subject = f"🟢 Yufeed Ingestion Complete - {total_new} new, {total_updated} updated"

    # Build HTML email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .header {{ background: {'#dc3545' if overall_status == 'FAILED' else '#28a745' if overall_status == 'SUCCESS' else '#ffc107'};
                      color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; background: #f8f9fa; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat {{ background: white; padding: 15px; border-radius: 8px; text-align: center; flex: 1; }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
            .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .source {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
            .source.failed {{ border-left-color: #dc3545; }}
            .source.partial {{ border-left-color: #ffc107; }}
            .error {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 4px; font-size: 12px; }}
            .error.critical {{ background: #f8d7da; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #e9ecef; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{status_emoji} Ingestion Report - {overall_status}</h1>
            <p>Completed at {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        <div class="content">
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{total_seen}</div>
                    <div class="stat-label">Documents Seen</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #28a745;">{total_new}</div>
                    <div class="stat-label">New Documents</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: #007bff;">{total_updated}</div>
                    <div class="stat-label">Updated</div>
                </div>
                <div class="stat">
                    <div class="stat-value" style="color: {'#dc3545' if total_errors > 0 else '#28a745'};">{total_errors}</div>
                    <div class="stat-label">Errors</div>
                </div>
            </div>

            <h2>Source Details</h2>
    """

    for report in reports:
        status_class = "failed" if report.status == "failed" else "partial" if report.status == "partial" else ""
        duration = (report.completed_at - report.started_at).total_seconds()

        html += f"""
            <div class="source {status_class}">
                <h3>{report.source_name}</h3>
                <table>
                    <tr><td>Status</td><td><strong>{report.status.upper()}</strong></td></tr>
                    <tr><td>Duration</td><td>{duration:.1f} seconds</td></tr>
                    <tr><td>Documents Seen</td><td>{report.items_seen}</td></tr>
                    <tr><td>New</td><td>{report.items_new}</td></tr>
                    <tr><td>Updated</td><td>{report.items_updated}</td></tr>
                    <tr><td>Skipped</td><td>{report.items_skipped}</td></tr>
                    <tr><td>Errors</td><td>{len(report.errors)}</td></tr>
                </table>
        """

        if report.errors:
            html += "<h4>Errors:</h4>"
            for error in report.errors[:10]:  # Limit to 10 errors
                error_msg = error.get("error", "Unknown error")
                entry_link = error.get("entry", "N/A")
                html += f"""
                    <div class="error critical">
                        <strong>Error:</strong> {error_msg[:200]}<br>
                        <strong>Entry:</strong> {entry_link}
                    </div>
                """
            if len(report.errors) > 10:
                html += f"<p><em>... and {len(report.errors) - 10} more errors</em></p>"

        html += "</div>"

    html += """
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated message from Yufeed Sentinel.<br>
                <a href="http://localhost:3000">Open Dashboard</a>
            </p>
        </div>
    </body>
    </html>
    """

    success = send_email(recipient, subject, html)
    if success:
        logger.info(f"Ingestion report sent to {recipient}")
    else:
        logger.error(f"Failed to send ingestion report to {recipient}")

    return success


def send_ingestion_failure_alert(
    source_name: str,
    error_message: str,
    to_email: Optional[str] = None,
) -> bool:
    """
    Send immediate alert when ingestion fails critically.
    """
    recipient = to_email or settings.ADMIN_EMAIL or settings.EMAILS_FROM_EMAIL

    subject = f"🚨 CRITICAL: Yufeed Ingestion Failed - {source_name}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .alert {{ background: #dc3545; color: white; padding: 20px; border-radius: 8px; }}
            .content {{ padding: 20px; background: #f8f9fa; }}
            .error-box {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; }}
            pre {{ background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="alert">
            <h1>🚨 Ingestion Failed</h1>
            <p>Source: <strong>{source_name}</strong></p>
            <p>Time: {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        <div class="content">
            <div class="error-box">
                <h3>Error Details</h3>
                <pre>{error_message[:2000]}</pre>
            </div>
            <p>
                <strong>Action Required:</strong> Please check the ingestion logs and retry manually if needed.
            </p>
            <p style="color: #666; font-size: 12px;">
                <a href="http://localhost:3000">Open Dashboard</a>
            </p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient, subject, html)
