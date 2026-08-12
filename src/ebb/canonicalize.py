import re

# Collapses infrastructure-wrapper syntax down to the bare model id a provider's own API would
# use directly, so the same underlying model is recognized as the same canonical id regardless
# of which cloud layer referenced it. Every pattern here is verified against live vendor docs
# (CLAUDE_CODE_PLAN.md's "never write a contract from memory" applies to this too):
#
# - AWS Bedrock cross-Region inference profile IDs are exactly "{region}.{vendor}.{model-id}",
#   e.g. `us.anthropic.claude-3-haiku-20240307-v1:0` — this literal example is drawn straight
#   from AWS's own inference-profiles-support docs, not invented.
# - Bedrock (profile or plain) model IDs carry a trailing "-v{N}:{M}" version suffix.
# - GCP Vertex AI publisher-model resource names are "publishers/{publisher}/models/{model}",
#   optionally prefixed "projects/{project}/locations/{location}/" — confirmed against Google's
#   own REST reference for the publisherModels resource.
# - Vertex AI model *versions* use a trailing "@{N}" suffix — this is GCP's general resource
#   versioning convention (used across several GCP APIs), not confirmed against a Claude-
#   specific example, so treat it as a well-hedged structural rule rather than a cited fact.
#
# Deliberately NOT handled here: stripping "-latest" / "-preview" style suffixes. Some of those
# are curated as their own whole registry entries (e.g. `chatgpt-4o-latest`, which OpenAI
# deprecated as an alias in its own right — see src/ebb/registries/retirements/openai.yaml).
# Stripping the suffix here would silently break that entry's resolution. A floating alias
# that ISN'T itself curated stays exactly as unresolvable after canonicalization as it was
# before — see resolve()'s tests (Session 4) for why that's correct, not a gap.
_BEDROCK_REGION_PREFIX = re.compile(r"^(us|eu|apac|us-gov)\.")
_BEDROCK_VENDOR_PREFIX = re.compile(
    r"^(anthropic|amazon|meta|mistral|cohere|ai21|openai|deepseek|writer)\."
)
_BEDROCK_VERSION_SUFFIX = re.compile(r"(-v\d+)?:\d+$")
_VERTEX_VERSION_SUFFIX = re.compile(r"@\d+$")
_VERTEX_RESOURCE_PATH = re.compile(
    r"^(?:projects/[^/]+/locations/[^/]+/)?publishers/[^/]+/models/(?P<model_id>.+)$"
)


def canonicalize(raw_text: str) -> str:
    """Pure and isolated, per CLAUDE_CODE_PLAN.md Session 5 — no registry lookup, no I/O, no
    dependency on anything but its own input. Idempotent (canonicalize(canonicalize(x)) ==
    canonicalize(x) for all x) and round-trips (any of this module's recognized wrapper forms
    of a given model canonicalizes to the same result as the model's own bare id) — both
    verified by the property tests in tests/unit/test_canonicalize.py.
    """
    text = raw_text.strip()

    vertex_match = _VERTEX_RESOURCE_PATH.match(text)
    if vertex_match:
        text = vertex_match.group("model_id")

    text = _VERTEX_VERSION_SUFFIX.sub("", text)
    text = _BEDROCK_VERSION_SUFFIX.sub("", text)

    region_match = _BEDROCK_REGION_PREFIX.match(text)
    if region_match:
        text = text[region_match.end() :]

    vendor_match = _BEDROCK_VENDOR_PREFIX.match(text)
    if vendor_match:
        text = text[vendor_match.end() :]

    return text
