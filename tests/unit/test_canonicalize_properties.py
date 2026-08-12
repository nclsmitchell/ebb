from hypothesis import given
from hypothesis import strategies as st

from ebb.canonicalize import canonicalize

_VENDORS = ["anthropic", "amazon", "meta", "mistral", "cohere", "ai21", "openai"]
_REGIONS = ["us", "eu", "apac", "us-gov"]

# Model-id-shaped strings that are already in canonical form — i.e. canonicalize() is a no-op
# on them. Excludes anything that could itself look like a wrapper form (a vendor name as the
# first segment, a trailing "-vN:M" or "@N" digit pattern) so the round-trip property below is
# well-defined: wrapping and then unwrapping a bare id must return that same bare id, not
# canonicalize(bare id), which only holds if canonicalize(bare id) == bare id to begin with.
_bare_ids = st.from_regex(r"[a-z][a-z]+-[a-z0-9]+(-[a-z0-9]+){1,3}", fullmatch=True).filter(
    lambda s: canonicalize(s) == s and s.split("-")[0] not in _VENDORS + _REGIONS
)


def _wrap(bare: str, region: str | None, vendor: str | None, version: str | None) -> str:
    text = bare
    if version == "bedrock":
        text += "-v1:0"
    text_with_vendor = f"{vendor}.{text}" if vendor else text
    text_with_region = f"{region}.{text_with_vendor}" if region and vendor else text_with_vendor
    if version == "vertex":
        text_with_region += "@1"
    return text_with_region


@given(
    bare=_bare_ids,
    region=st.one_of(st.none(), st.sampled_from(_REGIONS)),
    vendor=st.one_of(st.none(), st.sampled_from(_VENDORS)),
    version=st.one_of(st.none(), st.sampled_from(["bedrock", "vertex"])),
)
def test_any_bedrock_or_vertex_wrapper_form_round_trips_to_the_bare_id(
    bare: str, region: str | None, vendor: str | None, version: str | None
) -> None:
    wrapped = _wrap(bare, region, vendor, version)
    assert canonicalize(wrapped) == bare


@given(bare=_bare_ids, vendor=st.sampled_from(_VENDORS))
def test_vertex_resource_path_round_trips_to_the_bare_id(bare: str, vendor: str) -> None:
    short_path = f"publishers/{vendor}/models/{bare}"
    assert canonicalize(short_path) == bare

    full_path = f"projects/proj-1/locations/us-central1/publishers/{vendor}/models/{bare}"
    assert canonicalize(full_path) == bare


@given(st.text(min_size=0, max_size=80))
def test_canonicalize_is_idempotent_for_arbitrary_input(text: str) -> None:
    once = canonicalize(text)
    twice = canonicalize(once)
    assert once == twice


@given(bare=_bare_ids)
def test_canonicalize_is_a_no_op_on_already_bare_ids(bare: str) -> None:
    assert canonicalize(bare) == bare
