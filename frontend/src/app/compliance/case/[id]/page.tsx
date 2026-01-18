"use client";

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ComplianceProfile } from '@/types/compliance';
import RiskBadge from '@/components/compliance/RiskBadge';
import StatusChip from '@/components/compliance/StatusChip';

export default function CaseDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [caseDetails, setCaseDetails] = useState<ComplianceProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [reviewing, setReviewing] = useState(false);

    useEffect(() => {
        const fetchCase = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/compliance/cases/${params.id}`);
                if (res.ok) {
                    const data = await res.json();
                    setCaseDetails(data);
                } else {
                    console.error("Failed to fetch case");
                }
            } catch (error) {
                console.error("Error fetching case:", error);
            } finally {
                setLoading(false);
            }
        };

        if (params.id) {
            fetchCase();
        }
    }, [params.id]);

    const handleReview = async (action: 'approve' | 'reject') => {
        setReviewing(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/compliance/cases/${params.id}/review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action }),
            });

            if (res.ok) {
                const updatedCase = await res.json();
                setCaseDetails(updatedCase);
            }
        } catch (error) {
            console.error("Error submitting review:", error);
        } finally {
            setReviewing(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading case details...</div>;
    if (!caseDetails) return <div className="p-8 text-center">Case not found.</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link href="/compliance" className="text-sm text-gray-500 hover:text-gray-900">
                        ← Back to Dashboard
                    </Link>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Case #{caseDetails.id}
                    </h1>
                    <RiskBadge level={caseDetails.risk_level} />
                    <StatusChip status={caseDetails.status} />
                </div>

                <div className="flex gap-3">
                    {caseDetails.status === 'pending' && (
                        <>
                            <button
                                onClick={() => handleReview('reject')}
                                disabled={reviewing}
                                className="px-4 py-2 bg-white border border-rose-300 text-rose-700 rounded-lg text-sm font-medium hover:bg-rose-50 disabled:opacity-50"
                            >
                                Reject
                            </button>
                            <button
                                onClick={() => handleReview('approve')}
                                disabled={reviewing}
                                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 shadow-sm disabled:opacity-50"
                            >
                                Approve Application
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-3 gap-6">
                {/* Main Info Column */}
                <div className="col-span-2 space-y-6">
                    {/* Profile Information */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">
                            {caseDetails.type === 'kyc' ? 'Customer Information' : 'Business Information'}
                        </h2>
                        <div className="grid grid-cols-2 gap-y-4 text-sm">
                            {caseDetails.type === 'kyc' ? (
                                <>
                                    <div>
                                        <span className="block text-gray-500">Full Name</span>
                                        <span className="font-medium">{caseDetails.first_name} {caseDetails.last_name}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">Email</span>
                                        <span className="font-medium">{caseDetails.email}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">DOB</span>
                                        <span className="font-medium">{caseDetails.date_of_birth ? new Date(caseDetails.date_of_birth).toLocaleDateString() : 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">Phone</span>
                                        <span className="font-medium">{caseDetails.phone_number || 'N/A'}</span>
                                    </div>
                                    <div className="col-span-2">
                                        <span className="block text-gray-500">Address</span>
                                        <span className="font-medium">
                                            {caseDetails.address_line1}, {caseDetails.city}, {caseDetails.country}
                                        </span>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div>
                                        <span className="block text-gray-500">Company Name</span>
                                        <span className="font-medium">{caseDetails.company_name}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">Registration No.</span>
                                        <span className="font-medium">{caseDetails.registration_number}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">Jurisdiction</span>
                                        <span className="font-medium">{caseDetails.jurisdiction}</span>
                                    </div>
                                    <div>
                                        <span className="block text-gray-500">Website</span>
                                        <a href={caseDetails.website} target="_blank" className="font-medium text-blue-600 hover:underline">{caseDetails.website || 'N/A'}</a>
                                    </div>
                                    <div className="col-span-2">
                                        <span className="block text-gray-500">Industry</span>
                                        <span className="font-medium">{caseDetails.industry || 'N/A'}</span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Risk Signals */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Signals</h2>
                        {caseDetails.risk_signals.length === 0 ? (
                            <p className="text-gray-500 text-sm">No risk signals detected.</p>
                        ) : (
                            <div className="space-y-3">
                                {caseDetails.risk_signals.map((signal, i) => (
                                    <div key={i} className="flex items-start p-3 bg-gray-50 rounded-lg border border-gray-100">
                                        <div className={`mt-0.5 h-2 w-2 rounded-full mr-3 ${signal.score > 50 ? 'bg-red-500' : 'bg-yellow-500'}`}></div>
                                        <div>
                                            <div className="text-sm font-medium text-gray-900 capitalize">{signal.signal_type.replace('_', ' ')}</div>
                                            <div className="text-xs text-gray-500">{signal.description}</div>
                                        </div>
                                        <div className="ml-auto text-xs font-bold text-gray-400">
                                            Score: {signal.score}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Sidebar Column */}
                <div className="space-y-6">
                    {/* Documents */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                        <h2 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">Documents</h2>
                        <div className="space-y-3">
                            {caseDetails.documents.map((doc, i) => (
                                <div key={i} className="flex items-center p-2 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer">
                                    <div className="h-8 w-8 bg-blue-100 text-blue-600 rounded flex items-center justify-center text-xs font-bold mr-3">
                                        📄
                                    </div>
                                    <div className="flex-1 overflow-hidden">
                                        <div className="text-sm font-medium text-gray-900 truncate capitalize">{doc.document_type.replace('_', ' ')}</div>
                                        <div className="text-xs text-green-600">{doc.verification_status}</div>
                                    </div>
                                </div>
                            ))}
                            {caseDetails.documents.length === 0 && (
                                <p className="text-gray-500 text-xs">No documents uploaded.</p>
                            )}
                        </div>
                        <button className="mt-4 w-full py-2 text-xs font-medium text-gray-600 border border-dashed border-gray-300 rounded hover:bg-gray-50">
                            + Request Document
                        </button>
                    </div>

                    {/* Meta Info */}
                    <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                        <div className="text-xs text-gray-500 space-y-2">
                            <div className="flex justify-between">
                                <span>Created</span>
                                <span>{new Date(caseDetails.created_at).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Last Updated</span>
                                <span>{new Date(caseDetails.updated_at).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Profile ID</span>
                                <span className="font-mono">{caseDetails.id}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
