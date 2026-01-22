'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CaseDetailPage() {
  const { case_id: caseId } = useParams();
  const router = useRouter();

  const [caseData, setCaseData] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [regulations, setRegulations] = useState<any[]>([]);
  const [assignTo, setAssignTo] = useState('');
  const [team, setTeam] = useState('');
  const [escalationNotes, setEscalationNotes] = useState('');
  const [closeOutcome, setCloseOutcome] = useState('no_action');
  const [closeNotes, setCloseNotes] = useState('');

  useEffect(() => {
    if (caseId) {
      fetchCase();
      fetchRelated();
    }
  }, [caseId]);

  const fetchCase = async () => {
    const res = await fetch(`${API_URL}/api/cases/${caseId}`);
    const data = await res.json();
    setCaseData(data);
  };

  const fetchRelated = async () => {
    const [alertsRes, txsRes, regsRes] = await Promise.all([
      fetch(`${API_URL}/api/cases/${caseId}/alerts`),
      fetch(`${API_URL}/api/cases/${caseId}/transactions`),
      fetch(`${API_URL}/api/cases/${caseId}/regulations`)
    ]);
    setAlerts(await alertsRes.json());
    setTransactions(await txsRes.json());
    setRegulations(await regsRes.json());
  };

  const handleAssign = async () => {
    await fetch(`${API_URL}/api/cases/${caseId}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_to: assignTo, team })
    });
    fetchCase();
  };

  const handleEscalate = async () => {
    await fetch(`${API_URL}/api/cases/${caseId}/escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ escalation_notes: escalationNotes })
    });
    fetchCase();
  };

  const handleClose = async () => {
    await fetch(`${API_URL}/api/cases/${caseId}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        outcome: closeOutcome,
        outcome_notes: closeNotes
      })
    });
    fetchCase();
  };

  if (!caseData) {
    return <p className="p-4">Chargement du cas…</p>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Case {caseData.case_id}</h1>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <p><strong>Statut :</strong> {caseData.status}</p>
        <p><strong>Priorité :</strong> {caseData.priority}</p>
        <p><strong>Gravité :</strong> {caseData.severity}</p>
        <p><strong>Sujet :</strong> {caseData.subject_type} – {caseData.subject_id}</p>
        <p><strong>Description :</strong> {caseData.description}</p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Assigner le cas</h2>
        <input
          type="text"
          placeholder="Assigné à…"
          value={assignTo}
          onChange={(e) => setAssignTo(e.target.value)}
          className="border p-2 rounded mb-2 w-full"
        />
        <input
          type="text"
          placeholder="Équipe (optionnel)"
          value={team}
          onChange={(e) => setTeam(e.target.value)}
          className="border p-2 rounded mb-2 w-full"
        />
        <button onClick={handleAssign} className="bg-blue-600 text-white px-3 py-2 rounded">
          Assigner
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Escalader le cas</h2>
        <textarea
          placeholder="Notes pour l’escalade…"
          value={escalationNotes}
          onChange={(e) => setEscalationNotes(e.target.value)}
          className="border p-2 rounded mb-2 w-full"
        />
        <button onClick={handleEscalate} className="bg-orange-600 text-white px-3 py-2 rounded">
          Escalader
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Clôturer le cas</h2>
        <select
          value={closeOutcome}
          onChange={(e) => setCloseOutcome(e.target.value)}
          className="border p-2 rounded mb-2 w-full"
        >
          <option value="no_action">Aucune action</option>
          <option value="sar_filed">SAR déposée</option>
          <option value="account_closed">Compte fermé</option>
          <option value="escalated">Escalated</option>
          <option value="resolved">Résolu</option>
        </select>
        <textarea
          placeholder="Notes de clôture…"
          value={closeNotes}
          onChange={(e) => setCloseNotes(e.target.value)}
          className="border p-2 rounded mb-2 w-full"
        />
        <button onClick={handleClose} className="bg-red-600 text-white px-3 py-2 rounded">
          Clôturer
        </button>
      </div>

      <div>
        <h2 className="font-semibold mb-2">Alertes liées</h2>
        <ul className="list-disc pl-5">
          {alerts.map((a) => (
            <li key={a.alert_id}>
              {a.alert_id} – {a.alert_type} – {a.severity}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h2 className="font-semibold mb-2">Transactions liées</h2>
        <ul className="list-disc pl-5">
          {transactions.map((t) => (
            <li key={t.transaction_id}>
              {t.transaction_id} – {t.amount} {t.currency}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h2 className="font-semibold mb-2">Textes réglementaires liés</h2>
        <ul className="list-disc pl-5">
          {regulations.map((r) => (
            <li key={r.id}>
              {r.celex} – {r.title}
            </li>
          ))}
        </ul>
      </div>

      <button
        onClick={() => router.push(`/network-analysis?user=${caseData.subject_id}`)}
        className="mt-4 bg-purple-600 text-white px-4 py-2 rounded"
      >
        Analyser le réseau du sujet
      </button>
    </div>
  );
}
