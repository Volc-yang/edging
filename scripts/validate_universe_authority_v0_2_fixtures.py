#!/usr/bin/env python3
"""Read-only I0E contract oracle; no production imports, writer, or Genesis."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import argparse
import hashlib
import hmac
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct

DOMAIN = "edgeworld.universe.authority"
PREFIX = b"edgeworld.universe.authority\x00v0.2\x00"
MAX_INT = (1 << 53) - 1
ID = re.compile(r"[a-z][a-z0-9._-]{0,63}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
CLASSES = {"synthetic-contract-only", "genesis-runtime"}
PLACES = ("city", "wildland", "plain", "forest", "river_marsh", "ocean")


class Invalid(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(ok, code):
    if not ok:
        raise Invalid(code)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), "SCHEMA")


def uint(value):
    require(type(value) is int and 0 <= value <= MAX_INT, "INTEGER")


def ident(value):
    require(type(value) is str and ID.fullmatch(value) is not None, "ID")


def hashref(value):
    require(type(value) is str and HASH.fullmatch(value) is not None, "REFERENCE")


def scalar(value):
    require(type(value) is dict and set(value) == {"$f64"}, "F64")
    bits = value["$f64"]
    require(type(bits) is str and re.fullmatch(r"[0-9a-f]{16}", bits) is not None, "F64")
    number = struct.unpack(">d", bytes.fromhex(bits))[0]
    require(math.isfinite(number), "F64")
    return number


def tree(value, depth=0):
    require(depth <= 32, "LIMIT")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(abs(value) <= MAX_INT, "INTEGER")
    elif type(value) is str:
        try:
            size = len(value.encode("utf-8", "strict"))
        except UnicodeError as exc:
            raise Invalid("UNICODE") from exc
        require(size <= 4096, "LIMIT")
    elif type(value) is list:
        require(len(value) <= 256, "LIMIT")
        for item in value:
            tree(item, depth + 1)
    elif type(value) is dict:
        require(len(value) <= 64, "LIMIT")
        for key, item in value.items():
            require(type(key) is str, "SCHEMA")
            tree(key, depth + 1)
            tree(item, depth + 1)
        if "$f64" in value:
            scalar(value)
    else:
        raise Invalid("NUMBER")


def canonical(value):
    """Independent container encoder, not production canonical or I7 checker."""
    if value is None:
        return b"null"
    if type(value) is bool:
        return b"true" if value else b"false"
    if type(value) is int:
        return str(value).encode("ascii")
    if type(value) is str:
        return json.dumps(value, ensure_ascii=True).encode("ascii")
    if type(value) is list:
        return b"[" + b",".join(canonical(x) for x in value) + b"]"
    if type(value) is dict:
        return b"{" + b",".join(canonical(k) + b":" + canonical(value[k])
                                 for k in sorted(value)) + b"}"
    raise Invalid("NUMBER")


def digest(record):
    return hashlib.sha256(PREFIX + canonical(record)).hexdigest()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def number(_):
    raise Invalid("NUMBER")


def integer_token(token):
    require(len(token.removeprefix("-")) <= 16, "INTEGER")
    value = int(token)
    require(abs(value) <= MAX_INT, "INTEGER")
    return value


def parse(raw, maximum):
    require(type(raw) is bytes and len(raw) <= maximum, "LIMIT")
    try:
        text = raw.decode("utf-8", "strict")
        require(not text.startswith("\ufeff"), "UNICODE")
        return json.loads(text, object_pairs_hook=pairs, parse_int=integer_token,
                          parse_float=number, parse_constant=number)
    except UnicodeError as exc:
        raise Invalid("UNICODE") from exc
    except RecursionError as exc:
        raise Invalid("LIMIT") from exc
    except json.JSONDecodeError as exc:
        raise Invalid("JSON") from exc


def wire(raw):
    require(type(raw) is bytes, "JSON")
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    require(b"\n" not in raw and b"\r" not in raw, "JSON")
    return parse(raw, 1048576)


def influence(previous, current):
    with localcontext() as ctx:
        ctx.prec = 2000
        ctx.rounding = ROUND_HALF_EVEN
        return int(((Decimal.from_float(current) - Decimal.from_float(previous)) * Decimal(1000))
                   .to_integral_value(rounding=ROUND_HALF_EVEN))


def runtime_key_allowed(key):
    require(type(key) is bytes and len(key) == 32 and key != bytes(range(32)), "AUTHORIZATION")


def bound_head(binding, context):
    """Pure public binding, supplied by trusted owner/worker, never the response."""
    exact(context, {"world_id", "authority_root", "trust_algorithm", "trust_anchor",
                    "artifact_class", "expected_build", "expected_options"})
    exact(binding, set(context) | {"head", "domain", "version", "profile", "storage_state"})
    require(binding["authority_root"] == context["authority_root"], "ROOT_MISMATCH")
    root = binding["authority_root"]
    require(type(root) is str and root.startswith("/") and not root.startswith("//")
            and "\x00" not in root and ".." not in PurePosixPath(root).parts
            and str(PurePosixPath(root)) == root, "ROOT_MISMATCH")
    require(all(binding[k] == v for k, v in context.items()), "AUTHORIZATION")
    require(binding["domain"] == DOMAIN and binding["version"] == "0.2"
            and binding["profile"] == "composite-rigid-support.v0.2"
            and binding["storage_state"] in ("ready", "unconfirmed_readonly")
            and binding["trust_algorithm"] == "local-hmac-sha256.v0.2"
            and binding["artifact_class"] in CLASSES, "PROFILE")
    ident(binding["world_id"])
    for key in ("trust_anchor", "expected_build", "expected_options"):
        hashref(binding[key])
    hashref(binding["head"])
    return binding["head"]


class FixtureVerifier:
    """Only the public test key: a statically injected owner context, never JSON trust."""
    def __init__(self, key, context):
        require(type(key) is bytes and len(key) == 32, "AUTHORIZATION")
        require(context["artifact_class"] == "synthetic-contract-only", "AUTHORIZATION")
        self.key = key
        self.world = context["world_id"]
        self.root = context["authority_root"]
        require(type(self.root) is str and self.root.startswith("/") and "\x00" not in self.root
                and not self.root.startswith("//") and ".." not in PurePosixPath(self.root).parts
                and str(PurePosixPath(self.root)) == self.root, "ROOT_MISMATCH")
        self.anchor = sha(b"edgeworld.universe.trust-anchor\x00v0.2\x00" + self.world.encode("ascii")
                          + b"\x00" + self.root.encode("utf-8") + b"\x00" + key)
        self.assert_context(context)

    def assert_context(self, context):
        require(context["artifact_class"] == "synthetic-contract-only", "AUTHORIZATION")
        require(context["authority_root"] == self.root, "ROOT_MISMATCH")
        require(context["world_id"] == self.world and context["trust_anchor"] == self.anchor
                and context["trust_algorithm"] == "local-hmac-sha256.v0.2", "AUTHORIZATION")

    def __call__(self, record):
        require(record["world_id"] == self.world and record["kind"] in {"approval", "admission"}, "AUTHORIZATION")
        unsigned = dict(record, body={k: v for k, v in record["body"].items() if k != "auth_tag"})
        message = (b"edgeworld.universe.receipt\x00v0.2\x00" + self.anchor.encode("ascii") + b"\x00"
                   + record["kind"].encode("ascii") + b"\x00" + canonical(unsigned))
        expected = hmac.new(self.key, message, hashlib.sha256).hexdigest()
        require(hmac.compare_digest(expected, record["body"]["auth_tag"]), "AUTHORIZATION")


class Oracle:
    def __init__(self, schema, receipt_verifier=None):
        self.schema = schema
        self.limits = schema["limits"]
        self.receipt_verifier = receipt_verifier

    def field(self, value, spec):
        if spec == "id":
            ident(value)
        elif spec == "hash":
            hashref(value)
        elif spec == "nullable_hash":
            if value is not None:
                hashref(value)
        elif spec == "uint":
            uint(value)
        elif spec == "sint":
            require(type(value) is int and abs(value) <= MAX_INT, "INTEGER")
        elif spec == "f64":
            scalar(value)
        elif spec == "nullable_mm":
            require(value is None or type(value) is int and abs(value) <= 1000, "PHYSICS_INVALID")
        elif spec in {"delta", "steps", "blob_size"}:
            uint(value)
            require(value in (0, 1) if spec == "delta" else
                    value <= self.schema["physics_parameters"]["horizon_advances"] * 8 if spec == "steps" else 0 < value <= 8388608,
                    "BLOB_LIMIT" if spec == "blob_size" else "LIMIT")
        elif spec == "nullable_case":
            require(value in (None, "weak", "strong"), "SCHEMA")
        elif spec == "class":
            require(type(value) is str and value in CLASSES, "PROFILE")
        elif spec == "media":
            require(value in ("application/x-edgeworld-static-vector",
                              "application/x-genesis-gstraj;version=1.4.3"), "PROFILE")
        elif spec == "output":
            require(type(value) is str and len(value) <= 1024, "SCHEMA")
        elif spec == "json_object":
            require(type(value) is dict, "SCHEMA")
        elif spec == "i7_config":
            require(canonical(value) == canonical(self.schema["physics_parameters"]), "PROFILE")
        elif spec == "signs":
            require(canonical(value) == b"[1,-1,1]", "SCHEMA")
        elif spec == "vec3":
            require(type(value) is list and len(value) == 3, "SCHEMA")
            for x in value:
                scalar(x)
        elif spec == "extent":
            require(type(value) is list and len(value) == 4, "GEOGRAPHY")
            for x in value:
                self.field(x, "sint")
            require(value[0] < value[2] and value[1] < value[3], "GEOGRAPHY")
        elif spec in {"polygon", "polyline"}:
            require(type(value) is list and (4 if spec == "polygon" else 2) <= len(value) <= 256, "GEOGRAPHY")
            for point in value:
                require(type(point) is list and len(point) == 2, "GEOGRAPHY")
                for x in point:
                    self.field(x, "sint")
            if spec == "polygon":
                require(value[0] == value[-1], "GEOGRAPHY")
        elif spec == "ids":
            require(type(value) is list and 2 <= len(value) <= 6, "GEOGRAPHY")
            for x in value:
                ident(x)
            require(len(value) == len(set(value)), "ID")
        elif spec in {"assets", "decorations", "sources", "dependencies", "bindings", "bodies", "contacts"}:
            self.entries(value, spec)
        else:
            require(type(value) is str and value in spec.split("|"), "SCHEMA")

    def entries(self, values, kind):
        require(type(values) is list, "SCHEMA")
        limits = {"assets": 64, "decorations": 1000, "sources": 32, "dependencies": 16,
                  "bindings": 2, "bodies": 2, "contacts": 32}
        require(len(values) <= limits[kind], "LIMIT")
        identities = []
        for item in values:
            if kind == "assets":
                exact(item, {"asset_id", "uri", "content_sha256", "byte_count", "source", "use", "license_status", "dependencies"})
                ident(item["asset_id"]); hashref(item["content_sha256"]); uint(item["byte_count"])
                require(item["source"] == "installed-ue-5.8.3-basicshapes"
                        and item["use"] == "technical-proxy-not-realism"
                        and item["license_status"] == "ue-installed-content-no-shipping-review", "ASSET")
                require(type(item["uri"]) is str and re.fullmatch(r"/Engine/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+", item["uri"]) is not None, "ASSET")
                require(type(item["dependencies"]) is list, "ASSET")
                for x in item["dependencies"]:
                    ident(x)
                require(len(set(item["dependencies"])) == len(item["dependencies"]), "ASSET")
                identities.append(item["asset_id"])
            elif kind == "decorations":
                exact(item, {"instance_id", "place_id", "asset_id", "position_cm", "scale_milli"})
                for key in ("instance_id", "place_id", "asset_id"):
                    ident(item[key])
                for key in ("position_cm", "scale_milli"):
                    require(type(item[key]) is list and len(item[key]) == 3, "SCHEMA")
                    for x in item[key]:
                        self.field(x, "sint")
                require(all(x > 0 for x in item["scale_milli"]), "SCHEMA")
                identities.append(item["instance_id"])
            elif kind == "sources":
                exact(item, {"path", "sha256"}); hashref(item["sha256"])
                require(type(item["path"]) is str and not item["path"].startswith("/")
                        and ".." not in item["path"].split("/"), "BUILD")
                identities.append(item["path"])
            elif kind == "dependencies":
                exact(item, {"name", "version", "metadata_sha256"}); hashref(item["metadata_sha256"])
                require(type(item["name"]) is str and type(item["version"]) is str, "BUILD")
                identities.append(item["name"])
            elif kind == "bindings":
                exact(item, {"physical_id", "existence_id", "genesis_name", "role", "config_entity_index"})
                for key in ("physical_id", "existence_id", "genesis_name"):
                    ident(item[key])
                uint(item["config_entity_index"])
                require(item["role"] in ("dynamic", "support"), "PHYSICS_INVALID")
                identities.append(item["physical_id"])
            elif kind == "bodies":
                exact(item, {"physical_id", "position_m", "quaternion_wxyz", "linear_velocity_m_s", "angular_velocity_rad_s", "mass_kg"})
                ident(item["physical_id"]); identities.append(item["physical_id"])
                for key, length, bound in (("position_m", 3, 10), ("quaternion_wxyz", 4, 1.001),
                                           ("linear_velocity_m_s", 3, 100), ("angular_velocity_rad_s", 3, 100)):
                    require(type(item[key]) is list and len(item[key]) == length, "PHYSICS_INVALID")
                    require(all(abs(scalar(x)) <= bound for x in item[key]), "PHYSICS_INVALID")
                mass = scalar(item["mass_kg"])
                # Only the frozen fixed-support identity admits signed zero.
                require(item["physical_id"] in ("body-dynamic", "body-support")
                        and abs(sum(scalar(x)**2 for x in item["quaternion_wxyz"]) - 1) <= 1e-4
                        and (mass >= 0 if item["physical_id"] == "body-support" else mass > 0),
                        "PHYSICS_INVALID")
            elif kind == "contacts":
                exact(item, {"pair", "position_m", "force_on_dynamic_n"})
                require(item["pair"] == ["body-dynamic", "body-support"], "PHYSICS_INVALID")
                self.field(item["position_m"], "vec3"); self.field(item["force_on_dynamic_n"], "vec3")
                require(all(abs(scalar(x)) <= 10 for x in item["position_m"])
                        and all(abs(scalar(x)) <= 1e6 for x in item["force_on_dynamic_n"]), "PHYSICS_INVALID")
        if kind != "contacts":
            require(len(identities) == len(set(identities)), "ID")
        if kind in {"bindings", "bodies"}:
            require(identities == ["body-dynamic", "body-support"], "PHYSICS_INVALID")
        if kind == "assets":
            require(identities == sorted(identities)
                    and sum(item["byte_count"] for item in values) <= 2147483648, "ASSET")
        if kind == "contacts":
            require(values == sorted(values, key=lambda x: (x["pair"], [y["$f64"] for y in x["position_m"]],
                                                           [y["$f64"] for y in x["force_on_dynamic_n"]])), "PHYSICS_INVALID")

    def required_refs(self, record):
        kind = record["kind"]
        refs = self.schema["refs"][kind]
        if kind == "route":
            return {"p" + str(i): "place" for i in range(len(record["body"]["place_ids"]))}
        result = {key.rstrip("?"): val for key, val in refs.items()}
        if kind == "manifest" and record["body"]["revision"] == 0:
            return {"state": "state"}
        if kind == "event" and "prior_event" not in record["refs"]:
            result.pop("prior_event")
        return result

    def record(self, record):
        tree(record)
        exact(record, {"domain", "version", "world_id", "kind", "id", "body", "refs"})
        require(record["domain"] == DOMAIN and record["version"] == "0.2", "DOMAIN")
        ident(record["world_id"]); ident(record["id"])
        k = record["kind"]
        require(type(k) is str and k in self.schema["body"], "SCHEMA")
        exact(record["body"], self.schema["body"][k])
        for name, spec in self.schema["body"][k].items():
            self.field(record["body"][name], spec)
        exact(record["refs"], self.required_refs(record))
        for ref in record["refs"].values():
            hashref(ref)
        require(len(canonical(record)) <= self.schema["kind_bytes"][k], "LIMIT")

    def target(self, records, record, ref):
        value = record["refs"][ref]
        require(value in records, "REFERENCE")
        return records[value]

    def static_record(self, r, records, context):
        b, k = r["body"], r["kind"]
        get = lambda name: self.target(records, r, name)
        if "artifact_class" in b:
            require(b["artifact_class"] == context["artifact_class"], "PROFILE")
        if k == "existence":
            require(r["id"] == b["existence_id"], "ID")
        elif k == "unit_transform":
            require(scalar(b["scale"]) == 100, "PHYSICS_INVALID")
        elif k == "provider_build":
            require(digest(r) == context["expected_build"], "BUILD")
            if context["artifact_class"] == "genesis-runtime":
                require(b["adapter_source_sha256"] is not None, "BUILD")
        elif k == "resolved_options":
            require(digest(r) == context["expected_options"] and r["refs"]["build"] == context["expected_build"], "BUILD")
            require(b["resolution"] == ("static-declared" if context["artifact_class"] == "synthetic-contract-only" else "runtime-exported"), "BUILD")
            if b["resolution"] == "runtime-exported":
                exact(b["exports"], {"sim_options", "rigid_options", "dynamic_morph", "support_morph", "rigid_material"})
                require(all(type(x) is dict and bool(x) for x in b["exports"].values()), "BUILD")
        elif k == "physics_config":
            require(r["refs"]["build"] == context["expected_build"]
                    and r["refs"]["options"] == context["expected_options"]
                    and get("options")["refs"]["build"] == r["refs"]["build"]
                    and get("options")["body"]["parameter_hash"] == sha(canonical(b["config"])), "BUILD")
        elif k == "physics_binding":
            entities = get("config")["body"]["config"]["entities"]
            for i, binding in enumerate(b["bindings"]):
                e = entities[i]
                require(binding == {"physical_id": e["physical_id"], "existence_id": e["existence_id"],
                                    "genesis_name": e["genesis_name"], "role": "dynamic" if i == 0 else "support",
                                    "config_entity_index": i}, "PHYSICS_INVALID")
                existence = get("dynamic_exists" if i == 0 else "support_exists")["body"]
                require(existence["existence_id"] == binding["existence_id"] and existence["category"] == "physical", "REFERENCE")
        elif k in {"physics_sample", "checkpoint_descriptor", "physics_snapshot"}:
            require(get("binding")["refs"]["config"] == r["refs"]["config"], "PHYSICS_INVALID")
            if k == "checkpoint_descriptor":
                synthetic = b["artifact_class"] == "synthetic-contract-only"
                require(b["format"] == ("synthetic-static-bytes" if synthetic else "genesis-gstraj")
                        and b["media_type"] == ("application/x-edgeworld-static-vector" if synthetic else
                                                "application/x-genesis-gstraj;version=1.4.3")
                        and r["refs"]["build"] == get("config")["refs"]["build"], "PROFILE")
            if k == "physics_snapshot":
                require(all(get(name)["refs"]["config"] == r["refs"]["config"] and
                            get(name)["refs"]["binding"] == r["refs"]["binding"] for name in ("sample", "checkpoint")), "PHYSICS_INVALID")
                require((b["case_id"] == "initial") == (b["physical_step_count"] == 0), "PHYSICS_INVALID")
        elif k == "route":
            require([get("p" + str(i))["body"]["place_id"] for i in range(len(b["place_ids"]))] == b["place_ids"], "GEOGRAPHY")
        elif k == "watercourse":
            require(get("upstream")["body"]["place_kind"] == "forest" and get("marsh")["body"]["place_kind"] == "river_marsh"
                    and get("outlet")["body"]["place_kind"] == "ocean", "GEOGRAPHY")
        elif k == "place":
            require(get("existence")["body"]["category"] == "place", "REFERENCE")
        elif k == "asset_manifest":
            entries = {x["asset_id"]: x for x in b["entries"]}
            visiting, visited = set(), set()
            def visit(name):
                require(name in entries and name not in visiting, "ASSET")
                if name in visited:
                    return
                visiting.add(name)
                for dep in entries[name]["dependencies"]:
                    visit(dep)
                visiting.remove(name); visited.add(name)
            for name in entries:
                visit(name)
            require(b["dependency_status"] == ("declared-static" if context["artifact_class"] == "synthetic-contract-only" else "runtime-resolved"), "ASSET")
        elif k == "projection":
            ids = {x["asset_id"] for x in get("assets")["body"]["entries"]}
            require(all(x["asset_id"] in ids for x in b["decorations"]), "ASSET")
        elif k == "world_manifest":
            require(get("world_existence")["body"]["category"] == "world", "GEOGRAPHY")
            place_ids, existence_ids = [], [get("world_existence")["body"]["existence_id"],
                                          get("dynamic_existence")["body"]["existence_id"], get("support_existence")["body"]["existence_id"]]
            bounds = b["extent_cm"]
            for name in PLACES:
                place = get(name)
                require(place["body"]["place_kind"] == name, "GEOGRAPHY")
                place_ids.append(place["body"]["place_id"])
                existence_ids.append(self.target(records, place, "existence")["body"]["existence_id"])
                require(all(bounds[0] <= p[0] <= bounds[2] and bounds[1] <= p[1] <= bounds[3] for p in place["body"]["footprint_cm"]), "GEOGRAPHY")
            require(len(set(place_ids)) == 6 and len(set(existence_ids)) == 9, "ID")
            main = get("main_route")["body"]["place_ids"]
            branch = get("branch_route")["body"]["place_ids"]
            require(main == [get(x)["body"]["place_id"] for x in ("city", "plain", "forest", "river_marsh", "ocean")]
                    and branch == [get(x)["body"]["place_id"] for x in ("forest", "wildland")], "GEOGRAPHY")
            require(all(bounds[0] <= p[0] <= bounds[2] and bounds[1] <= p[1] <= bounds[3]
                        for name in ("main_route", "branch_route", "watercourse")
                        for p in get(name)["body"]["polyline_cm"]), "GEOGRAPHY")
            decorations = get("projection")["body"]["decorations"]
            require(all(x["place_id"] in place_ids for x in decorations), "GEOGRAPHY")
        elif k == "state":
            world = get("world")
            binding = self.target(records, get("snapshot"), "binding")
            require(binding["refs"]["dynamic_exists"] == world["refs"]["dynamic_existence"]
                    and binding["refs"]["support_exists"] == world["refs"]["support_existence"], "REFERENCE")
        elif k == "intent":
            require((b["action"] == "retain_snapshot" and b["tick_delta"] == 0
                     and b["case_id"] is None and b["budget"] == 0)
                    or (b["action"] == "physics_step" and b["tick_delta"] == 1
                        and b["case_id"] in ("weak", "strong")), "TRANSITION")
        elif k == "command":
            approval = get("approval")
            require(approval["refs"] == {"intent": r["refs"]["intent"], "proposal": r["refs"]["proposal"]}
                    and approval["body"]["principal"] == get("intent")["body"]["principal"]
                    == get("proposal")["body"]["principal"], "AUTHORIZATION")
        elif k == "candidate":
            previous, snapshot, command = get("prior_state"), get("snapshot"), get("command")
            intent = self.target(records, command, "intent"); ib = intent["body"]
            before = self.target(records, previous, "snapshot")
            require(b["revision"] == previous["body"]["revision"] + 1
                    and ib["expected_revision"] == previous["body"]["revision"]
                    and ib["random_cursor"] == previous["body"]["random_cursor"], "TRANSITION")
            require(intent["refs"]["config"] == snapshot["refs"]["config"] == before["refs"]["config"]
                    and intent["refs"]["binding"] == snapshot["refs"]["binding"] == before["refs"]["binding"], "PHYSICS_INVALID")
            if ib["action"] == "retain_snapshot":
                require(b["adapter_kind"] == "checkpoint_reuse" and r["refs"]["snapshot"] == previous["refs"]["snapshot"]
                        and b["tick"] == previous["body"]["tick"]
                        and b["influence_mm"] == previous["body"]["development_mm"], "TRANSITION")
            else:
                new_sample = self.target(records, snapshot, "sample")
                old_sample = self.target(records, before, "sample")
                require(b["adapter_kind"] == "genesis" and b["tick"] == previous["body"]["tick"] + 1
                        and snapshot["body"]["case_id"] == ib["case_id"]
                        and snapshot["body"]["physical_step_count"] == before["body"]["physical_step_count"] + 8
                        and b["influence_mm"] == influence(scalar(old_sample["body"]["bodies"][0]["position_m"][2]),
                                                          scalar(new_sample["body"]["bodies"][0]["position_m"][2])), "TRANSITION")
        elif k == "admission":
            candidate, command = get("candidate"), get("command")
            intent = self.target(records, command, "intent")
            approval = self.target(records, command, "approval")
            require(candidate["refs"]["command"] == r["refs"]["command"]
                    and b["principal"] == intent["body"]["principal"]
                    and b["evaluated_revision"] == intent["body"]["expected_revision"]
                    <= approval["body"]["expires_revision"], "AUTHORIZATION")
        elif k == "event":
            admission, state = get("admission"), get("state")
            candidate = self.target(records, admission, "candidate")
            previous = self.target(records, candidate, "prior_state")
            command = self.target(records, candidate, "command")
            intent = self.target(records, command, "intent")["body"]
            require(state["refs"]["snapshot"] == candidate["refs"]["snapshot"]
                    and state["refs"]["world"] == previous["refs"]["world"]
                    and all(state["body"][x] == candidate["body"][y] for x, y in
                            (("tick", "tick"), ("revision", "revision"), ("development_mm", "influence_mm")))
                    and state["body"]["budget"] == previous["body"]["budget"] - intent["budget"]
                    and state["body"]["random_cursor"] == previous["body"]["random_cursor"]
                    + (1 if intent["action"] == "physics_step" else 0), "TRANSITION")
            require((state["body"]["revision"] == 1 and "prior_event" not in r["refs"])
                    or (state["body"]["revision"] > 1 and "prior_event" in r["refs"]
                        and get("prior_event")["refs"]["state"] == candidate["refs"]["prior_state"]), "HEAD")
        elif k == "result":
            event = get("event"); admission = self.target(records, event, "admission")
            state = get("state"); candidate = self.target(records, admission, "candidate")
            intent = self.target(records, get("command"), "intent")
            require(r["refs"]["state"] == event["refs"]["state"]
                    and r["refs"]["command"] == admission["refs"]["command"]
                    and r["refs"]["checkpoint"] == candidate["refs"]["snapshot"], "REFERENCE")
            require(b == {"command_id": intent["body"]["command_id"], "tick": state["body"]["tick"],
                          "revision": state["body"]["revision"], "watermark": state["body"]["revision"]}, "WATERMARK")
        elif k == "index":
            result = get("result")
            require(b == {"command_id": result["body"]["command_id"], "fingerprint": result["refs"]["command"]}, "COMMAND_CONFLICT")

    def transition(self, manifest, records, context, authenticate=True):
        get = lambda record, name: self.target(records, record, name)
        body = manifest["body"]; state = get(manifest, "state"); sb = state["body"]
        require(body == {"tick": sb["tick"], "revision": sb["revision"], "watermark": sb["revision"]}, "WATERMARK")
        snapshot = get(state, "snapshot")
        if body["revision"] == 0:
            require(body["tick"] == 0 and sb["development_mm"] is None and sb["random_cursor"] == 0
                    and sb["budget"] == 8
                    and snapshot["body"] == {"case_id": "initial", "physical_step_count": 0}, "HEAD")
            return
        prior = get(manifest, "prior_manifest"); previous = get(prior, "state")
        event = get(manifest, "event"); result = get(get(manifest, "index"), "result")
        admission = get(event, "admission"); command = get(admission, "command")
        candidate = get(admission, "candidate"); intent = get(command, "intent"); ib = intent["body"]
        approval = get(command, "approval"); proposal = get(command, "proposal")
        require(body["revision"] == prior["body"]["revision"] + 1
                and state["refs"]["world"] == previous["refs"]["world"]
                and event["refs"]["state"] == manifest["refs"]["state"] == result["refs"]["state"]
                and result["refs"]["event"] == manifest["refs"]["event"]
                and event["refs"].get("prior_event") == prior["refs"].get("event"), "HEAD")
        require(candidate["refs"]["prior_state"] == prior["refs"]["state"]
                and candidate["refs"]["command"] == admission["refs"]["command"] == result["refs"]["command"]
                and candidate["refs"]["snapshot"] == state["refs"]["snapshot"] == result["refs"]["checkpoint"], "REFERENCE")
        require(approval["refs"] == {"proposal": command["refs"]["proposal"], "intent": command["refs"]["intent"]}
                and proposal["body"]["principal"] == ib["principal"] == approval["body"]["principal"] == admission["body"]["principal"], "AUTHORIZATION")
        require(ib["expected_revision"] == previous["body"]["revision"] == admission["body"]["evaluated_revision"]
                and ib["random_cursor"] == previous["body"]["random_cursor"]
                and admission["body"]["evaluated_revision"] <= approval["body"]["expires_revision"], "AUTHORIZATION")
        if authenticate:
            require(callable(self.receipt_verifier), "AUTHORIZATION")
            self.receipt_verifier(approval)
            self.receipt_verifier(admission)
        require(candidate["body"]["revision"] == sb["revision"]
                and candidate["body"]["tick"] == sb["tick"]
                and candidate["body"]["influence_mm"] == sb["development_mm"], "TRANSITION")
        before = get(previous, "snapshot")
        require(intent["refs"]["config"] == snapshot["refs"]["config"] == before["refs"]["config"]
                and intent["refs"]["binding"] == snapshot["refs"]["binding"] == before["refs"]["binding"], "PHYSICS_INVALID")
        if ib["action"] == "retain_snapshot":
            require(ib["tick_delta"] == 0 and ib["case_id"] is None and ib["budget"] == 0
                    and candidate["body"]["adapter_kind"] == "checkpoint_reuse"
                    and previous["refs"]["snapshot"] == state["refs"]["snapshot"]
                    and sb["tick"] == previous["body"]["tick"]
                    and all(sb[x] == previous["body"][x] for x in ("development_mm", "budget", "random_cursor")), "TRANSITION")
        else:
            current_sample, old_sample = get(snapshot, "sample"), get(before, "sample")
            znew = scalar(current_sample["body"]["bodies"][0]["position_m"][2])
            zold = scalar(old_sample["body"]["bodies"][0]["position_m"][2])
            require(ib["tick_delta"] == 1 and ib["case_id"] in ("weak", "strong")
                    and candidate["body"]["adapter_kind"] == "genesis"
                    and sb["tick"] == previous["body"]["tick"] + 1
                    and snapshot["body"]["case_id"] == ib["case_id"]
                    and snapshot["body"]["physical_step_count"] == before["body"]["physical_step_count"] + 8
                    and sb["development_mm"] == influence(zold, znew)
                    and sb["budget"] == previous["body"]["budget"] - ib["budget"]
                    and sb["random_cursor"] == previous["body"]["random_cursor"] + 1, "TRANSITION")
        require(result["body"] == {"command_id": ib["command_id"], "tick": sb["tick"],
                                   "revision": sb["revision"], "watermark": sb["revision"]}, "WATERMARK")
        index = get(manifest, "index")
        require(index["body"] == {"command_id": ib["command_id"], "fingerprint": result["refs"]["command"]}, "COMMAND_CONFLICT")

    def archive(self, archive, context, blobs):
        require(self.receipt_verifier is not None, "AUTHORIZATION")
        self.receipt_verifier.assert_context(context)
        exact(archive, {"domain", "version", "test_profile", "artifact_class", "records", "head"})
        require(archive["domain"] == DOMAIN and archive["version"] == "0.2", "DOMAIN")
        require(archive["test_profile"] == "composite-rigid-support.v0.2"
                and archive["artifact_class"] == context["artifact_class"], "PROFILE")
        require(len(canonical(archive)) <= 16777216 and type(archive["records"]) is list
                and 1 <= len(archive["records"]) <= 2048, "LIMIT")
        records, identities, event_ids, commands = {}, set(), set(), {}
        for record in archive["records"]:
            self.record(record)
            require(record["world_id"] == context["world_id"], "WORLD")
            key = (record["kind"], record["id"])
            require(key not in identities, "ID"); identities.add(key)
            for name, reference in record["refs"].items():
                require(reference in records and records[reference]["kind"] == self.required_refs(record)[name], "REFERENCE")
            d = digest(record); records[d] = record
            self.static_record(record, records, context)
            if record["kind"] in {"approval", "admission"}:
                require(callable(self.receipt_verifier), "AUTHORIZATION")
                self.receipt_verifier(record)
            if record["kind"] == "command":
                intent = self.target(records, record, "intent")["body"]
                key = (intent["principal"], intent["command_id"])
                require(key not in commands or commands[key] == d, "COMMAND_CONFLICT"); commands[key] = d
            if record["kind"] == "event":
                require(record["body"]["event_id"] not in event_ids, "ID"); event_ids.add(record["body"]["event_id"])
            if record["kind"] == "manifest":
                self.transition(record, records, context)
        head = archive["head"]; hashref(head)
        require(head in records and records[head]["kind"] == "manifest", "REFERENCE")
        retained, committed, binary_refs, reachable = [], {}, {}, set()
        def reach(d):
            if d in reachable:
                return
            reachable.add(d)
            r = records[d]
            for child in r["refs"].values():
                reach(child)
            if r["kind"] == "checkpoint_descriptor":
                b = r["body"]; h = b["payload_sha256"]
                require(h in blobs and len(blobs[h]) == b["byte_count"] and sha(blobs[h]) == h, "CORRUPT")
                meta = (b["byte_count"], b["media_type"], b["artifact_class"])
                require(h not in binary_refs or binary_refs[h] == meta, "CORRUPT"); binary_refs[h] = meta
        current = head
        while current:
            require(current not in retained, "REFERENCE"); retained.append(current)
            manifest = records[current]
            if "index" in manifest["refs"]:
                index = self.target(records, manifest, "index"); result = self.target(records, index, "result")
                intent = self.target(records, self.target(records, result, "command"), "intent")["body"]
                key = (intent["principal"], intent["command_id"])
                require(key not in committed, "COMMAND_CONFLICT"); committed[key] = index["refs"]["result"]
            current = manifest["refs"].get("prior_manifest")
        require(len(retained) <= 64, "COUNTS"); reach(head)
        require(sum(x[0] for x in binary_refs.values()) <= 536870912, "BLOB_LIMIT")
        return {"records": records, "retained": tuple(retained), "commands": committed,
                "binary_refs": binary_refs, "counts": self.inventory(records, head, retained, binary_refs, blobs)}

    def inventory(self, records, head, retained, binary_refs, blobs):
        current = set()
        def visit(d):
            if d in current:
                return
            current.add(d)
            for child in records[d]["refs"].values():
                visit(child)
        visit(records[head]["refs"]["state"])
        kinds = Counter(records[d]["kind"] for d in current)
        require(len(current) <= 288, "COUNTS")
        assets = next(records[d]["body"] for d in current if records[d]["kind"] == "asset_manifest")
        decorations = next(records[d]["body"]["decorations"] for d in current if records[d]["kind"] == "projection")
        points = sum(len(records[d]["body"]["footprint_cm" if records[d]["kind"] == "place" else "polyline_cm"])
                     for d in current if records[d]["kind"] in {"place", "route", "watercourse"})
        require(points <= 4096 and len(decorations) <= 1000, "COUNTS")
        return {"H": len(retained), "S_current": len(current), "S_by_kind": dict(sorted(kinds.items())),
                "D": len(decorations), "A_declared": len(assets["entries"]),
                "A_actual": len(assets["entries"]) if assets["dependency_status"] == "runtime-resolved" else None,
                "asset_dependency_status": assets["dependency_status"],
                "asset_bytes_declared": sum(x["byte_count"] for x in assets["entries"]),
                "asset_bytes_actual": sum(x["byte_count"] for x in assets["entries"]) if assets["dependency_status"] == "runtime-resolved" else None,
                "geometry_points": points, "json_objects": len(records),
                "json_bytes_by_kind": {k: sum(len(canonical(r)) for r in records.values() if r["kind"] == k)
                                       for k in sorted({r["kind"] for r in records.values()})},
                "all_json_canonical_bytes": sum(len(canonical(r)) for r in records.values()),
                "retained_raw_unique_files": len(binary_refs), "retained_raw_unique_bytes": sum(x[0] for x in binary_refs.values()),
                "all_supplied_raw_bytes": sum(len(x) for x in blobs.values()),
                "unreferenced_raw_bytes": sum(len(v) for k, v in blobs.items() if k not in binary_refs)}

    def proof(self, raw, context, *, expected_request_id, tick, revision, watermark, trusted_head):
        trusted_storage_state = trusted_head["storage_state"] if type(trusted_head) is dict else None
        trusted_head = bound_head(trusted_head, context)
        env = wire(raw)
        exact(env, {"protocol_version", "request_id", "ok", "result"})
        require(type(env["protocol_version"]) is int and env["protocol_version"] == 1
                and type(env["ok"]) is bool and env["ok"] is True, "SCHEMA")
        ident(expected_request_id); require(env["request_id"] == expected_request_id, "PROOF")
        for value in (tick, revision, watermark):
            uint(value)
        require(watermark == revision, "WATERMARK"); hashref(trusted_head)
        result = env["result"]
        exact(result, {"domain", "version", "world_id", "operation", "payload"})
        require(result["domain"] == DOMAIN and result["version"] == "0.2", "DOMAIN")
        require(result["world_id"] == context["world_id"] and result["operation"] == "observe", "WORLD")
        p = result["payload"]
        exact(p, {"manifest", "state", "event", "watermark", "storage_state", "artifact_class",
                  "head", "membership", "records", "opaque_refs"})
        require(p["storage_state"] in ("ready", "unconfirmed_readonly")
                and p["artifact_class"] == context["artifact_class"], "PROFILE")
        require(p["storage_state"] == trusted_storage_state, "PROOF")
        require(type(p["watermark"]) is int and p["watermark"] == watermark, "WATERMARK")
        require(p["head"] == trusted_head, "PROOF")
        require(type(p["membership"]) is list and 1 <= len(p["membership"]) <= 64
                and type(p["records"]) is list and len(p["records"]) <= 96
                and type(p["opaque_refs"]) is list and len(p["opaque_refs"]) <= 256, "PROOF_LIMIT")
        all_records = p["membership"] + p["records"] + [p["manifest"], p["state"]]
        if p["event"] is not None:
            all_records.append(p["event"])
        records, identities = {}, {}
        for r in all_records:
            self.record(r); require(r["world_id"] == context["world_id"], "WORLD")
            d = digest(r); key = (r["kind"], r["id"])
            require(key not in identities or identities[key] == d, "ID"); identities[key] = d
            records[d] = r
        # Type-check every supplied edge before any recursive dependency expansion.
        # Wrong-kind shared DAGs must not amplify traversal before rejection.
        for r in records.values():
            expected_refs = self.required_refs(r)
            for name, ref in r["refs"].items():
                if ref in records:
                    require(records[ref]["kind"] == expected_refs[name], "PROOF")
        counts = Counter(r["kind"] for r in all_records)
        require(all(counts[k] <= n for k, n in self.schema["proof_kind_max"].items()), "PROOF_LIMIT")
        auxiliary = [digest(r) for r in p["records"]]
        explicit = {digest(r) for r in p["membership"] + [p["manifest"], p["state"]]
                    + ([p["event"]] if p["event"] is not None else [])}
        require(len(auxiliary) == len(set(auxiliary)) and not set(auxiliary) & explicit, "PROOF")
        selected = digest(p["manifest"])
        membership = p["membership"]
        require(all(r["kind"] == "manifest" for r in membership)
                and len({digest(r) for r in membership}) == len(membership)
                and digest(membership[0]) == trusted_head and digest(membership[-1]) == selected, "PROOF")
        for a, b in zip(membership, membership[1:]):
            require(a["refs"].get("prior_manifest") == digest(b)
                    and a["body"]["revision"] == b["body"]["revision"] + 1
                    and a["body"]["tick"] - b["body"]["tick"] in (0, 1), "PROOF")
        require(p["manifest"]["body"] == {"tick": tick, "revision": revision, "watermark": watermark}
                and p["manifest"]["refs"]["state"] == digest(p["state"]), "WATERMARK")
        require((p["event"] is None and revision == 0) or (p["event"] is not None and revision > 0
                and p["manifest"]["refs"]["event"] == digest(p["event"])), "PROOF")
        previous_hash = p["manifest"]["refs"].get("prior_manifest")
        needed = {selected}
        if previous_hash:
            require(previous_hash in records, "PROOF"); needed.add(previous_hash)
        expanded, active = set(), set()
        def expand(d, mode="normal"):
            require(d in records, "PROOF")
            key = (d, mode)
            require(key not in active, "PROOF")
            if key in expanded:
                return
            active.add(key)
            needed.add(d); r = records[d]
            for name, ref in r["refs"].items():
                if r["kind"] == "manifest" and (name == "prior_manifest" or mode == "previous" and name != "state"):
                    continue
                if r["kind"] == "event" and name == "prior_event":
                    continue
                expand(ref)
            active.remove(key)
            expanded.add(key)
        expand(selected)
        if previous_hash:
            expand(previous_hash, "previous")
        membership_hashes = {digest(r) for r in membership}
        require(set(records) == needed | membership_hashes, "PROOF")
        opaque = set()
        for d, r in records.items():
            for name, ref in r["refs"].items():
                if ref in records:
                    require(records[ref]["kind"] == self.required_refs(r)[name], "PROOF")
                else:
                    allowed = r["kind"] == "event" and name == "prior_event"
                    allowed |= r["kind"] == "manifest" and d != selected and name != "state"
                    allowed |= r["kind"] == "manifest" and d in membership_hashes - {selected, previous_hash}
                    require(allowed, "PROOF"); opaque.add(ref)
            if r["kind"] not in {"manifest", "event", "candidate", "admission", "command", "approval", "proposal", "result", "index", "intent"}:
                self.static_record(r, records, context)
        require(p["opaque_refs"] == sorted(opaque), "PROOF")
        self.transition(p["manifest"], records, context, authenticate=False)
        require(len(canonical(env)) <= 1048576, "PROOF_LIMIT")
        return {"manifest": selected, "state": p["state"], "event": p["event"],
                "storage_state": p["storage_state"], "artifact_class": p["artifact_class"],
                "scope": "selected-slice-membership-only-not-full-history-or-raw-validation",
                "bytes": len(raw) - (1 if raw.endswith(b"\n") else 0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).resolve().parents[1] / "doc/fixtures/universe_authority_v0_2")
    args = parser.parse_args(); directory = args.fixtures
    files = sorted(directory.glob("*.json"))
    before = {p.name: sha(p.read_bytes()) for p in files}
    def load(name, cap=67108864):
        return parse((directory / name).read_bytes(), cap)
    schema, context = load("schema.json"), load("trust_context.json")
    key = bytes.fromhex(load("fixture_key.json")["key_hex"])
    verifier = FixtureVerifier(key, context)
    checker = Oracle(schema, verifier)
    worst = sum(schema["kind_bytes"][k] * n for k, n in schema["proof_kind_max"].items()) + schema["proof_wrapper_reserve"]
    require(worst <= 1048576, "PROOF_LIMIT")
    archive = load("positive.json", 16777216)
    blob_input = load("synthetic_blobs.json")
    blobs = {h: bytes.fromhex(value) for h, value in blob_input["blobs"].items()}
    report = checker.archive(archive, context, blobs)
    source_manifest = load("source_manifest.json")
    exact(source_manifest, {"scope", "files"})
    require(source_manifest["scope"] == "read-only-installed-package-python-sources", "BUILD")
    source_files = source_manifest["files"]
    require(type(source_files) is list and len(source_files) <= 4096, "BUILD")
    for entry in source_files:
        exact(entry, {"path", "sha256"}); hashref(entry["sha256"])
        require(type(entry["path"]) is str and not entry["path"].startswith("/")
                and ".." not in entry["path"].split("/") and entry["path"].endswith(".py"), "BUILD")
    require([x["path"] for x in source_files] == sorted({x["path"] for x in source_files}), "BUILD")
    build = report["records"][context["expected_build"]]["body"]
    require(build["source_file_count"] == len(source_files)
            and build["source_tree_sha256"] == sha(canonical(source_files))
            and all(x in source_files for x in build["critical_sources"]), "BUILD")
    golden = load("golden.json")
    require(len(golden) == len(archive["records"]), "GOLDEN")
    for r, expected in zip(archive["records"], golden):
        require(r["id"] == expected["id"] and r["kind"] == expected["kind"]
                and canonical(r).hex() == expected["canonical_hex"] and digest(r) == expected["sha256"], "GOLDEN")
    require(report["counts"] == load("inventory.json"), "COUNTS")
    proofs = load("proof_vectors.json")
    for case in proofs:
        result = checker.proof(case["raw"].encode(), context, **case["expected"])
        require(result["manifest"] == case["selected_manifest"], "PROOF")
    negatives = load("negative.json")
    for case in negatives:
        try:
            ctx = case.get("context", context)
            if case["operation"] == "archive":
                checker.archive(parse(case["raw"].encode(), 16777216), ctx, blobs)
            elif case["operation"] == "proof":
                checker.proof(case["raw"].encode(), ctx, **case["expected"])
            elif case["operation"] == "blob":
                supplied = dict(blobs)
                if case["bytes_hex"] is None:
                    supplied.pop(case["sha256"])
                else:
                    supplied[case["sha256"]] = bytes.fromhex(case["bytes_hex"])
                checker.archive(archive, context, supplied)
            elif case["operation"] == "runtime_key":
                runtime_key_allowed(bytes.fromhex(case["key_hex"]))
            else:
                value = parse(case["raw"].encode(), 1048576); tree(value)
        except Invalid as exc:
            require(exc.code == case["error"], "NEGATIVE_CODE:" + case["name"] + ":" + exc.code)
        else:
            raise Invalid("NEGATIVE_ACCEPTED:" + case["name"])
    require(before == {p.name: sha(p.read_bytes()) for p in files}, "FIXTURE_CHANGED")
    print(json.dumps({"status": "PASS_STATIC_CONTRACT_ONLY", "records": len(archive["records"]),
                      "retained_roots": len(report["retained"]), "golden": len(golden),
                      "negative_vectors": len(negatives), "proof_vectors": len(proofs),
                      "proof_worst_bytes": worst, "counts": report["counts"],
                      "fixture_json_unchanged": True, "genesis_runtime": "not_run"}, sort_keys=True))


if __name__ == "__main__":
    main()
