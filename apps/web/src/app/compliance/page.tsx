"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { ComplianceProfile } from '@/types/compliance';
import { RiskBadge } from '@/components/ui/risk-badge';
import StatusChip from '@/components/compliance/StatusChip';
import { fetchWithAuth } from '@/lib/auth';

export default function ComplianceDashboard() {
    const [cases, setCases] = useState<ComplianceProfile[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch cases from API
        // Assuming API is at localhost:8000 or proxied
        const fetchCases = async () => {
            try {
                // Adjust URL based on actual setup. Assuming direct for now or env var.
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetchWithAuth(`${apiUrl}/compliance/cases`);
                if (res.ok) {
                    const data = await res.json();
                    setCases(data);
                } else {
                    console.error("Failed to fetch cases");
                }
            } catch (error) {
                console.error("Error fetching cases:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchCases();
    }, []);

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-semibold text-gray-900">Compliance Dashboard</h1>
                    <p className="text-sm text-gray-500 mt-1">Monitor and review KYC/KYB applications.</p>
                </div>
                <div className="flex gap-3">
                    <button className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                        Export Report
                    </button>
                    <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm">
                        + New Application
                    </button>
                </div>
            </header>

            {/* Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                {[
                    { label: 'Pending Reviews', value: cases.filter(c => c.status === 'pending').length, color: 'border-l-4 border-yellow-400' },
                    { label: 'High Risk', value: cases.filter(c => c.risk_level === 'high').length, color: 'border-l-4 border-rose-500' },
                    { label: 'Approved Today', value: cases.filter(c => c.status === 'approved').length, color: 'border-l-4 border-blue-500' }, // Mock calculation
                    { label: 'Total Cases', value: cases.length, color: 'border-l-4 border-gray-300' },
                ].map((stat, i) => (
                    <div key={i} className={`bg-white p-4 rounded-lg shadow-sm border border-gray-100 ${stat.color}`}>
                        <div className="text-sm text-gray-500 font-medium">{stat.label}</div>
                        <div className="text-2xl font-semibold text-gray-900 mt-1">{stat.value}</div>
                    </div>
                ))}
            </div>

            {/* Cases Table */}
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h2 className="text-base font-medium text-gray-900">Recent Applications</h2>
                    <div className="flex gap-2">
                        {['All', 'Pending', 'High Risk'].map(filter => (
                            <button key={filter} className="text-xs font-medium px-3 py-1.5 rounded-full bg-white border border-gray-200 text-gray-600 hover:border-gray-300">
                                {filter}
                            </button>
                        ))}
                    </div>
                </div>

                {loading ? (
                    <div className="p-8 text-center text-gray-500">Loading cases...</div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entity</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Level</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {cases.map((c) => (
                                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="h-8 w-8 rounded bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 mr-3">
                                                {c.type === 'kyb' ? 'B' : 'C'}
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium text-gray-900">
                                                    {c.type === 'kyb' ? c.company_name : `${c.first_name} ${c.last_name}`}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {c.type === 'kyb' ? c.registration_number : c.email}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-xs font-medium text-gray-500 uppercase">{c.type}</span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(c.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <RiskBadge level={c.risk_level} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <StatusChip status={c.status} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <Link href={`/compliance/case/${c.id}`} className="text-indigo-600 hover:text-indigo-900">
                                            View
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
