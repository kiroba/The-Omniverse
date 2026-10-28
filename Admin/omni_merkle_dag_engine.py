#!/usr/bin/env python3
"""
==============================================================================
OMNIVERSE MERKLE DAG STATE SYNC & CONFLICT RESOLVER [v1.0.0]
==============================================================================
Implements a true Directed Acyclic Graph (DAG) for multi-author concurrent
event state. Supports:
- Multi-parent branch merging (parents: List[str])
- Deterministic Merkle Root calculation across DAG heads
- Last-Write-Wins (LWW) CRDT conflict resolution
==============================================================================
"""

import hashlib
import json
import time
import typing

class DAGNode:
    def __init__(self, action: str, author: str, payload: dict, parents: typing.List[str], timestamp: float = None):
        self.action = action
        self.author = author
        self.payload = payload
        self.parents = sorted(parents)
        self.timestamp = timestamp if timestamp else time.time()
        self.node_id = self.compute_hash()

    def compute_hash(self) -> str:
        canonical_struct = {
            "action": self.action,
            "author": self.author,
            "parents": self.parents,
            "payload": self.payload,
            "timestamp": self.timestamp
        }
        canonical_bytes = json.dumps(canonical_struct, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return "0x" + hashlib.sha256(canonical_bytes).hexdigest()

class MerkleDAGEngine:
    def __init__(self):
        self.nodes: typing.Dict[str, DAGNode] = {}
        self.heads: typing.Set[str] = set()

        # Create Genesis Node
        genesis = DAGNode("GENESIS", "0xGENESIS_AUTHOR", {"system": "Genesis Root"}, parents=[])
        self.nodes[genesis.node_id] = genesis
        self.heads.add(genesis.node_id)

    def add_node(self, action: str, author: str, payload: dict, parent_ids: typing.List[str] = None) -> DAGNode:
        if not parent_ids:
            parent_ids = list(self.heads)

        node = DAGNode(action, author, payload, parent_ids)
        self.nodes[node.node_id] = node

        # Update heads set: new node becomes a head, parents are no longer heads
        self.heads.add(node.node_id)
        for p_id in parent_ids:
            self.heads.discard(p_id)

        return node

    def compute_dag_merkle_root(self) -> str:
        sorted_heads = sorted(list(self.heads))
        combined = ":".join(sorted_heads).encode('utf-8')
        return "0x" + hashlib.sha256(combined).hexdigest()

    def resolve_lww_conflict(self, key: str, conflicting_nodes: typing.List[DAGNode]) -> DAGNode:
        """
        Last-Write-Wins (LWW) CRDT Conflict Resolution based on timestamp and author hash
        """
        best_node = max(conflicting_nodes, key=lambda n: (n.timestamp, n.author))
        return best_node

if __name__ == "__main__":
    dag = MerkleDAGEngine()
    node_a = dag.add_node("POST_CREATE", "0xALICE", {"text": "Hello Mesh!"})
    node_b = dag.add_node("POST_LIKE", "0xBOB", {"target": node_a.node_id})
    node_c = dag.add_node("MERGE_BRANCH", "0xCHARLIE", {"summary": "Sync point"}, parent_ids=[node_a.node_id, node_b.node_id])

    print("DAG Nodes Count:", len(dag.nodes))
    print("DAG Heads:", list(dag.heads))
    print("DAG Deterministic Merkle Root:", dag.compute_dag_merkle_root())
