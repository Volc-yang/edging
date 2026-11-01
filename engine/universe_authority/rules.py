"""Pure neutral fake candidate and bounded deterministic rule dependency checks."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import heapq
import math
import re

from .codec import ContractError, DOMAIN, VERSION, PROFILE, MAX_INTEGER, digest, encode_f64, f64
from .records import Record, validate_record

_ID = re.compile(r'[a-z][a-z0-9._-]{0,63}\Z')


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def neutral_candidate(prior: Record, command: Record, intent: Record, *, candidate_id: str) -> Record:
    for record, kind in ((prior, 'state'), (command, 'command'), (intent, 'intent')):
        validate_record(record)
        _require(record['kind'] == kind, 'SCHEMA')
    _require(prior['world_id'] == command['world_id'] == intent['world_id'], 'WORLD')
    _require(command['refs']['intent'] == digest(intent), 'REFERENCE')
    body, old = intent['body'], prior['body']
    _require(body['expected_revision'] == old['revision'], 'HEAD')
    _require(body['budget'] <= old['budget'] and body['random_cursor'] == old['random_cursor'],
             'TRANSITION')
    _require(old['revision'] < MAX_INTEGER and old['tick'] + body['tick_delta'] <= MAX_INTEGER
             and old['random_cursor'] < MAX_INTEGER, 'INTEGER')
    value = f64(old['value']['$f64']) + f64(body['transfer']['$f64'])
    _require(math.isfinite(value), 'TRANSITION')
    result = {'domain': DOMAIN, 'version': VERSION, 'world_id': prior['world_id'],
              'kind': 'candidate', 'id': candidate_id,
              'body': {'adapter_kind': 'fake', 'test_profile': PROFILE,
                       'value': encode_f64(value), 'tick': old['tick'] + body['tick_delta'],
                       'revision': old['revision'] + 1},
              'refs': {'command': digest(command), 'prior_state': digest(prior)}}
    validate_record(result)
    return result


def validate_rule_dag(nodes: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    """Return the lexicographically smallest topological order; no rule execution."""
    _require(isinstance(nodes, Mapping), 'SCHEMA')
    _require(len(nodes) <= 256, 'LIMIT')
    graph = {}
    for name, inputs in nodes.items():
        _require(type(name) is str and _ID.fullmatch(name) is not None, 'ID')
        _require(isinstance(inputs, Sequence) and not isinstance(inputs, (str, bytes, bytearray)), 'SCHEMA')
        _require(len(inputs) <= 256, 'LIMIT')
        for dependency in inputs:
            _require(type(dependency) is str and _ID.fullmatch(dependency) is not None, 'ID')
        _require(len(inputs) == len(set(inputs)) and name not in inputs, 'REFERENCE')
        graph[name] = tuple(inputs)
    for dependencies in graph.values():
        _require(all(name in graph for name in dependencies), 'REFERENCE')
    remaining = {name: len(dependencies) for name, dependencies in graph.items()}
    followers = {name: [] for name in graph}
    for name, dependencies in graph.items():
        for dependency in dependencies:
            followers[dependency].append(name)
    ready = [name for name, count in remaining.items() if not count]
    heapq.heapify(ready)
    output = []
    while ready:
        name = heapq.heappop(ready)
        output.append(name)
        for follower in followers[name]:
            remaining[follower] -= 1
            if not remaining[follower]:
                heapq.heappush(ready, follower)
    _require(len(output) == len(graph), 'REFERENCE')
    return tuple(output)
