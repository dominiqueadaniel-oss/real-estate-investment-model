import pytest

from investment_model.config import load_playbook
from investment_model.from_listing import MissingRequiredField, build_property_input
from investment_model.inputs import PropertyInput
from investment_model.report import evaluate_property


@pytest.fixture
def playbook():
    return load_playbook()


def test_missing_required_fields_raises(playbook):
    with pytest.raises(MissingRequiredField):
        build_property_input({"name": "X", "market": "Y"}, playbook)


def test_invalid_category_raises(playbook):
    raw = {
        "name": "X",
        "market": "Y",
        "category": "Flip",
        "purchase_price": 100000,
        "annual_rent_or_str_revenue": 12000,
    }
    with pytest.raises(MissingRequiredField):
        build_property_input(raw, playbook)


def test_minimal_ltr_raw_fills_every_gap(playbook):
    raw = {
        "name": "412 Oakwood Dr",
        "market": "Huntsville, AL",
        "category": "LTR",
        "purchase_price": 310000,
        "annual_rent_or_str_revenue": 28800,
    }
    prop_dict, assumptions = build_property_input(raw, playbook)
    assert len(assumptions) > 0
    assert prop_dict["acquisition"]["down_payment_pct"] == 0.20
    assert prop_dict["ltr_factors"]["school_rating"] == 5
    # Should build into a valid PropertyInput and evaluate without error.
    prop = PropertyInput.from_dict(prop_dict)
    report = evaluate_property(prop, playbook)
    assert report.decision in ("PURSUE", "CONSIDER", "REJECT")


def test_provided_fields_are_not_overridden(playbook):
    raw = {
        "name": "X",
        "market": "Y",
        "category": "LTR",
        "purchase_price": 300000,
        "annual_rent_or_str_revenue": 30000,
        "down_payment_pct": 0.25,
        "school_rating": 9,
    }
    prop_dict, assumptions = build_property_input(raw, playbook)
    assert prop_dict["acquisition"]["down_payment_pct"] == 0.25
    assert prop_dict["ltr_factors"]["school_rating"] == 9
    assumed_fields = {a.field for a in assumptions}
    assert "down_payment_pct" not in assumed_fields
    assert "school_rating" not in assumed_fields


def test_property_age_derived_from_year_built(playbook):
    raw = {
        "name": "X",
        "market": "Y",
        "category": "LTR",
        "purchase_price": 300000,
        "annual_rent_or_str_revenue": 30000,
        "year_built": 2010,
    }
    prop_dict, assumptions = build_property_input(raw, playbook)
    assert prop_dict["ltr_factors"]["property_age_years"] > 0
    assert any(a.field == "property_age_years" for a in assumptions)


def test_str_category_builds_str_factors_with_furniture_budget(playbook):
    raw = {
        "name": "Cabin",
        "market": "Sevier County, TN",
        "category": "STR",
        "purchase_price": 500000,
        "annual_rent_or_str_revenue": 85000,
    }
    prop_dict, _ = build_property_input(raw, playbook)
    assert "str_factors" in prop_dict
    assert "ltr_factors" not in prop_dict
    assert prop_dict["acquisition"]["furniture_budget"] == 15000


def test_appreciation_category_builds_appreciation_factors(playbook):
    raw = {
        "name": "SFH",
        "market": "Scottsdale, AZ",
        "category": "Appreciation",
        "purchase_price": 750000,
        "annual_rent_or_str_revenue": 36000,
    }
    prop_dict, _ = build_property_input(raw, playbook)
    assert "appreciation_factors" in prop_dict
    assert "ltr_factors" not in prop_dict
    assert "str_factors" not in prop_dict
