"""Decode the immutable Backend domain catalog, then bind its refs to real bytes.

This build-only adapter defines no domain DTO. It never imports Engine/package
initializers, providers or services. Calling it requires the selected domain
source closure and a separately pinned Pydantic build environment. Hashes and
catalog data do not grant installation, route, model or execution authority.
"""
from contextlib import contextmanager
import importlib
import importlib.abc
import importlib.util
import json
import sys
import types


DOMAIN_MODULES = (
    "contracts", "errors", "production_authorization", "registered_production", "bundle",
    "evidence", "current_final_evidence", "affected_repair", "plan_repair_targets",
    "affected_recipe", "component_diagnosis",
)
SOURCE_LIMIT = 16 * 1024 * 1024
DATA_LIMIT = 2 * 1024 * 1024
DIAGNOSTIC_FORMAT = "registered-production-driver-resources-v3-diagnostic-v1"


@contextmanager
def domain_models(selected, checked):
    """Load only the exact selected domain files; restore our private namespace."""
    prefix = "video_creator"
    if any(name == prefix or name.startswith(prefix + ".") for name in sys.modules):
        raise ValueError("Diagnostic build requires an isolated, unloaded Engine namespace")
    sources = {}
    for name in DOMAIN_MODULES:
        relative = "Code/video_creator/domain/" + name + ".py"
        if relative not in selected:
            raise ValueError("Missing immutable diagnostic grammar source: " + relative)
        fact, body = checked(selected[relative], SOURCE_LIMIT)
        if not body:
            raise ValueError("Empty immutable domain source: " + relative)
        sources["video_creator.domain." + name] = (fact, bytes(body))

    class Loader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            fact, body = sources[module.__name__]
            # Recheck the original file before and after executing its pinned
            # domain definitions; retain the exact bytes first observed.
            checked(fact, SOURCE_LIMIT)
            exec(compile(body, fact["path"], "exec"), module.__dict__)
            checked(fact, SOURCE_LIMIT)

    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname in sources:
                return importlib.util.spec_from_loader(fullname, Loader(), origin=sources[fullname][0]["path"])
            if fullname == prefix or fullname.startswith(prefix + "."):
                raise ImportError("Outside the fixed diagnostic domain closure: " + fullname)
            return None

    finder = Finder()
    try:
        for name in (prefix, prefix + ".domain"):
            module = types.ModuleType(name)
            module.__path__ = []
            module.__spec__ = importlib.util.spec_from_loader(name, loader=None, is_package=True)
            sys.modules[name] = module
        sys.modules[prefix].domain = sys.modules[prefix + ".domain"]
        sys.meta_path.insert(0, finder)
        catalog = importlib.import_module("video_creator.domain.component_diagnosis")
        contracts = importlib.import_module("video_creator.domain.contracts")
        alignment = importlib.import_module("video_creator.domain.affected_repair")
        routes = importlib.import_module("video_creator.domain.plan_repair_targets")
        yield catalog.ProductionDriverResourcesDiagnosticV1, contracts.CapabilityRoute, alignment.ForcedAlignmentRegistration, routes.plan_payload_sha256
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        for name in tuple(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


def encoded(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > DATA_LIMIT:
        raise ValueError("Bounded diagnostic catalog/route exceeds 2MiB")
    return body


def normalize_drivers(value, selected, checked):
    with domain_models(selected, checked) as (Catalog, _, __, ___):
        model = Catalog.model_validate_json(encoded(value))
        return model.model_dump(mode="json", by_alias=True)


def validate_bindings(drivers, bindings, registration, selected, resources, groups,
                      checked, document, relative):
    """Return provenance for exact catalog-to-installation byte relationships."""
    expected = {"rule_template_paths", "route_paths", "alignment_configuration", "alignment_license_paths"}
    if type(bindings) is not dict or set(bindings) != expected:
        raise ValueError("Exact diagnostic catalog byte bindings required")
    for key in ("rule_template_paths", "route_paths", "alignment_license_paths"):
        if type(bindings[key]) is not dict:
            raise ValueError("Catalog binding maps required: " + key)
    available = {**selected, **resources}
    facts = {}

    def member(name, digest=None, limit=None):
        name = relative(name)
        if name not in available:
            raise ValueError("Catalog member absent from complete source/resource maps: " + name)
        fact, _ = checked(available[name], limit)
        if fact["bytes"] == 0 or (digest is not None and fact["sha256"] != digest):
            raise ValueError("Catalog member body/hash differs: " + name)
        facts[name] = {**fact, "relative_path": name}
        return fact

    with domain_models(selected, checked) as (Catalog, Route, Alignment, route_sha256):
        catalog = Catalog.model_validate_json(encoded(drivers))
        recipes = catalog.recipes
        methods = catalog.diagnosis.methods
        template_ids = {method.rule_template_sha256 for method in methods}
        if set(bindings["rule_template_paths"]) != template_ids:
            raise ValueError("Template paths must cover every original method template hash exactly")
        for digest, name in bindings["rule_template_paths"].items():
            member(name, digest, DATA_LIMIT)
        for ref in [ref for recipe in recipes for ref in recipe.producer_source_refs] + [ref for method in methods for ref in method.implementation_source_refs]:
            member(ref.resource_name, ref.sha256, SOURCE_LIMIT)

        alignment_value = registration.get("alignment_registration")
        if (catalog.alignment is None) != (alignment_value is None):
            raise ValueError("Original alignment section/registration must both be present or null")
        alignment = None if alignment_value is None else Alignment.model_validate_json(encoded(alignment_value))
        route_ids = {ref.route_id for recipe in recipes for ref in recipe.routes} | {method.route.route_id for method in methods}
        if alignment is not None:
            route_ids.add(alignment.route_id)
        if set(bindings["route_paths"]) != route_ids:
            raise ValueError("Full original route files must cover catalog route IDs exactly")
        routes = {}
        for route_id, name in bindings["route_paths"].items():
            fact = member(name, limit=DATA_LIMIT)
            _, value = document(fact, DATA_LIMIT)
            route = Route.model_validate_json(encoded(value))
            if route.route_id != route_id or not route.verified:
                raise ValueError("Original selected verified route ID differs: " + route_id)
            routes[route_id] = route
        for recipe in recipes:
            for ref in recipe.routes:
                route = routes[ref.route_id]
                if route_sha256(route) != ref.route_sha256 or route.cost_rule_version != ref.cost_rule_version:
                    raise ValueError("Recipe differs from the full original route/cost rule: " + ref.route_id)
        for method in methods:
            if routes[method.route.route_id].model_dump(mode="json") != method.route.model_dump(mode="json"):
                raise ValueError("Diagnostic method differs from its full original route: " + method.method_id)

        section = catalog.alignment
        if section is None:
            if bindings["alignment_configuration"] is not None or bindings["alignment_license_paths"]:
                raise ValueError("No invented bindings for null alignment")
        else:
            for name, digest in section.model_files.items():
                member(name, digest)
            member(section.worker_resource)
            member(section.runtime_resource)
            member(bindings["alignment_configuration"], section.configuration_sha256, DATA_LIMIT)
            licenses = bindings["alignment_license_paths"]
            if set(licenses) != set(section.license_artifact_ids):
                raise ValueError("Original alignment license IDs require exact indexed documents")
            original_license_paths = {group["prefix"] + "/" + name for group in groups for name in group["license_files"]}
            for name in licenses.values():
                if relative(name) not in original_license_paths:
                    raise ValueError("Alignment license must be an original indexed group document")
                member(name, limit=DATA_LIMIT)
            route = routes[alignment.route_id]
            if route.capability != "alignment" or route.source != "owned_local" or route.credential_ref is not None or route.max_operation_cost.amount != 0:
                raise ValueError("Original local, credential-free, zero-cost alignment route required")
        grammar = {"Code/video_creator/domain/" + name + ".py": selected["Code/video_creator/domain/" + name + ".py"] for name in DOMAIN_MODULES}
        return {"domain_sources": grammar, "bindings": bindings,
                "members": [facts[name] for name in sorted(facts)],
                "status": "byte_bound_catalog_not_qualified"}
