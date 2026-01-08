"""
Network Analysis Service
Detect fraud rings and suspicious networks using graph analysis.

Identifies:
- Connected users (shared IPs, devices, counterparties)
- Circular transaction patterns
- Suspicious clusters
"""
from typing import Dict, List, Set, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from src.models.transaction_models import Transaction, UserRiskProfile

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """
    Analyzes transaction networks to detect fraud rings and suspicious patterns.
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_user_network(
        self,
        user_id: str,
        depth: int = 2,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze network of connections for a user.

        depth=1: Direct connections
        depth=2: Connections of connections (2-hop)
        depth=3: Extended network (3-hop)

        Returns network graph and risk indicators.
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Build network
        network = self._build_network(user_id, depth, start_date)

        # Analyze patterns
        circular_flows = self._detect_circular_flows(network)
        shared_attributes = self._find_shared_attributes(network)
        suspicious_clusters = self._identify_suspicious_clusters(network)

        # Calculate network risk score
        network_risk = self._calculate_network_risk(
            network,
            circular_flows,
            shared_attributes,
            suspicious_clusters
        )

        return {
            "user_id": user_id,
            "network_size": len(network['nodes']),
            "connection_count": len(network['edges']),
            "depth_analyzed": depth,
            "period_days": days,
            "network": network,
            "risk_indicators": {
                "circular_flows": circular_flows,
                "shared_attributes": shared_attributes,
                "suspicious_clusters": suspicious_clusters
            },
            "network_risk_score": network_risk,
            "risk_level": self._get_risk_level(network_risk)
        }

    def _build_network(
        self,
        user_id: str,
        depth: int,
        start_date: datetime
    ) -> Dict[str, Any]:
        """
        Build transaction network graph.

        Nodes: users
        Edges: transactions, shared attributes
        """
        nodes = set([user_id])
        edges = []
        current_level = {user_id}

        for level in range(depth):
            next_level = set()

            for current_user in current_level:
                # Find transactions from this user
                outgoing = self.db.query(Transaction).filter(
                    and_(
                        Transaction.user_id == current_user,
                        Transaction.timestamp >= start_date,
                        Transaction.counterparty_id.isnot(None)
                    )
                ).all()

                for tx in outgoing:
                    counterparty = tx.counterparty_id
                    if counterparty and counterparty not in nodes:
                        next_level.add(counterparty)

                    edges.append({
                        "source": current_user,
                        "target": counterparty or "UNKNOWN",
                        "type": "transaction",
                        "amount": float(tx.amount),
                        "currency": tx.currency,
                        "timestamp": tx.timestamp.isoformat(),
                        "transaction_id": tx.transaction_id
                    })

                # Find transactions to this user
                incoming = self.db.query(Transaction).filter(
                    and_(
                        Transaction.counterparty_id == current_user,
                        Transaction.timestamp >= start_date
                    )
                ).all()

                for tx in incoming:
                    sender = tx.user_id
                    if sender not in nodes:
                        next_level.add(sender)

                    edges.append({
                        "source": sender,
                        "target": current_user,
                        "type": "transaction",
                        "amount": float(tx.amount),
                        "currency": tx.currency,
                        "timestamp": tx.timestamp.isoformat(),
                        "transaction_id": tx.transaction_id
                    })

            nodes.update(next_level)
            current_level = next_level

            if not next_level:
                break

        # Get node details
        node_details = {}
        for node in nodes:
            profile = self.db.query(UserRiskProfile).filter(
                UserRiskProfile.user_id == node
            ).first()

            node_details[node] = {
                "user_id": node,
                "risk_level": profile.risk_level if profile else "unknown",
                "risk_score": float(profile.overall_risk_score) if profile and profile.overall_risk_score else 0,
                "total_alerts": profile.total_alerts if profile else 0
            }

        return {
            "nodes": list(nodes),
            "node_details": node_details,
            "edges": edges,
            "depth": depth
        }

    def _detect_circular_flows(self, network: Dict) -> List[Dict]:
        """
        Detect circular transaction flows (A -> B -> C -> A).

        Potential money laundering indicator.
        """
        edges = network['edges']
        circular_patterns = []

        # Build adjacency list
        graph = defaultdict(list)
        for edge in edges:
            if edge['type'] == 'transaction':
                graph[edge['source']].append({
                    'target': edge['target'],
                    'amount': edge['amount'],
                    'tx_id': edge['transaction_id']
                })

        # Find cycles using DFS
        visited = set()

        for start_node in graph.keys():
            if start_node in visited:
                continue

            cycles = self._find_cycles_from_node(graph, start_node, set(), [])
            for cycle in cycles:
                if len(cycle) >= 3:  # At least 3 nodes
                    circular_patterns.append({
                        "cycle": cycle,
                        "length": len(cycle),
                        "total_flow": sum(step['amount'] for step in cycle)
                    })

        return circular_patterns[:10]  # Return top 10

    def _find_cycles_from_node(
        self,
        graph: Dict,
        current: str,
        visited: Set[str],
        path: List[Dict],
        max_depth: int = 5
    ) -> List[List[Dict]]:
        """DFS to find cycles in graph."""
        if len(path) > max_depth:
            return []

        if current in visited and len(path) > 2:
            # Found a cycle
            cycle_start = next((i for i, step in enumerate(path) if step.get('node') == current), None)
            if cycle_start is not None:
                return [path[cycle_start:]]
            return []

        cycles = []
        visited.add(current)

        for neighbor in graph.get(current, []):
            new_path = path + [{
                'node': current,
                'target': neighbor['target'],
                'amount': neighbor['amount'],
                'tx_id': neighbor['tx_id']
            }]

            cycles.extend(
                self._find_cycles_from_node(
                    graph,
                    neighbor['target'],
                    visited.copy(),
                    new_path,
                    max_depth
                )
            )

        return cycles

    def _find_shared_attributes(self, network: Dict) -> Dict[str, List]:
        """
        Find users sharing suspicious attributes.

        - Same IP address
        - Same device fingerprint
        - Same session ID
        """
        nodes = network['nodes']

        if len(nodes) <= 1:
            return {}

        # Get transactions for all nodes
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id.in_(nodes)
        ).all()

        # Group by attributes
        by_ip = defaultdict(set)
        by_device = defaultdict(set)

        for tx in transactions:
            if tx.ip_address:
                by_ip[tx.ip_address].add(tx.user_id)
            if tx.device_fingerprint:
                by_device[tx.device_fingerprint].add(tx.user_id)

        # Find suspicious shared attributes (2+ users)
        shared = {}

        shared_ips = {ip: list(users) for ip, users in by_ip.items() if len(users) >= 2}
        if shared_ips:
            shared['shared_ips'] = shared_ips

        shared_devices = {dev: list(users) for dev, users in by_device.items() if len(users) >= 2}
        if shared_devices:
            shared['shared_devices'] = shared_devices

        return shared

    def _identify_suspicious_clusters(self, network: Dict) -> List[Dict]:
        """
        Identify suspicious clusters in the network.

        Clusters are suspicious if:
        - High interconnectivity
        - Multiple high-risk users
        - Large transaction volumes
        """
        nodes = network['nodes']
        edges = network['edges']
        node_details = network['node_details']

        if len(nodes) < 3:
            return []

        # Calculate clustering metrics
        clusters = []

        # Simple clustering: users with 3+ connections
        connection_count = defaultdict(int)
        for edge in edges:
            connection_count[edge['source']] += 1
            connection_count[edge['target']] += 1

        highly_connected = [
            node for node, count in connection_count.items()
            if count >= 3
        ]

        for center_node in highly_connected:
            # Get connected nodes
            connected = set()
            total_volume = 0

            for edge in edges:
                if edge['source'] == center_node:
                    connected.add(edge['target'])
                    total_volume += edge['amount']
                elif edge['target'] == center_node:
                    connected.add(edge['source'])
                    total_volume += edge['amount']

            # Check if cluster is suspicious
            high_risk_count = sum(
                1 for node in connected
                if node_details.get(node, {}).get('risk_level') in ['high', 'critical']
            )

            if high_risk_count >= 2 or total_volume > 100000:
                clusters.append({
                    "center_node": center_node,
                    "connected_nodes": list(connected),
                    "connection_count": len(connected),
                    "high_risk_members": high_risk_count,
                    "total_volume": total_volume,
                    "suspicion_score": (high_risk_count * 30) + (len(connected) * 10)
                })

        return sorted(clusters, key=lambda x: x['suspicion_score'], reverse=True)[:5]

    def _calculate_network_risk(
        self,
        network: Dict,
        circular_flows: List,
        shared_attributes: Dict,
        clusters: List
    ) -> float:
        """
        Calculate overall network risk score (0-100).
        """
        score = 0.0

        # Circular flows (high risk indicator)
        if circular_flows:
            score += min(len(circular_flows) * 15, 40)

        # Shared attributes (identity fraud indicator)
        if shared_attributes:
            shared_ip_count = len(shared_attributes.get('shared_ips', {}))
            shared_device_count = len(shared_attributes.get('shared_devices', {}))
            score += min((shared_ip_count + shared_device_count) * 10, 30)

        # Suspicious clusters
        if clusters:
            score += min(len(clusters) * 10, 20)

        # High-risk node density
        node_details = network['node_details']
        high_risk_nodes = sum(
            1 for details in node_details.values()
            if details.get('risk_level') in ['high', 'critical']
        )
        risk_density = high_risk_nodes / len(node_details) if node_details else 0
        score += risk_density * 10

        return min(score, 100.0)

    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level."""
        if score >= 75:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 25:
            return 'medium'
        else:
            return 'low'

    def find_related_users(
        self,
        user_id: str,
        relationship_type: str = "all"
    ) -> List[str]:
        """
        Find users related to a given user.

        relationship_type:
        - "transaction": Connected via transactions
        - "ip": Shared IP address
        - "device": Shared device fingerprint
        - "all": Any relationship
        """
        related = set()

        if relationship_type in ["transaction", "all"]:
            # Find via transactions
            transactions = self.db.query(Transaction).filter(
                or_(
                    Transaction.user_id == user_id,
                    Transaction.counterparty_id == user_id
                )
            ).all()

            for tx in transactions:
                if tx.user_id != user_id:
                    related.add(tx.user_id)
                if tx.counterparty_id and tx.counterparty_id != user_id:
                    related.add(tx.counterparty_id)

        if relationship_type in ["ip", "all"]:
            # Find via shared IP
            user_txs = self.db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).all()

            user_ips = {tx.ip_address for tx in user_txs if tx.ip_address}

            if user_ips:
                ip_matches = self.db.query(Transaction).filter(
                    Transaction.ip_address.in_(user_ips)
                ).all()

                related.update(tx.user_id for tx in ip_matches if tx.user_id != user_id)

        if relationship_type in ["device", "all"]:
            # Find via shared device
            user_txs = self.db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).all()

            user_devices = {tx.device_fingerprint for tx in user_txs if tx.device_fingerprint}

            if user_devices:
                device_matches = self.db.query(Transaction).filter(
                    Transaction.device_fingerprint.in_(user_devices)
                ).all()

                related.update(tx.user_id for tx in device_matches if tx.user_id != user_id)

        return list(related)
