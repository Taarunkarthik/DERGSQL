import pytest

from app.extraction import parse_extraction_json


def test_extraction_json_schema_validates_candidate():
    result = parse_extraction_json(
        '{"incident_type":"collision","location_text":"Junction A",'
        '"severity":"high","delay_seconds":300,"closure":false,"confidence":0.85,'
        '"latitude":12.9,"longitude":77.5}'
    )
    assert result.incident_type == "collision"
    assert result.confidence == 0.85


def test_extraction_rejects_invalid_json_and_unknown_fields():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_extraction_json("not json")
    with pytest.raises(ValueError, match="Invalid extracted"):
        parse_extraction_json(
            '{"incident_type":"collision","location_text":"X","severity":"extreme",'
            '"confidence":0.9,"unverified_claim":"x"}'
        )


def test_coordinates_must_be_paired():
    with pytest.raises(ValueError, match="both be supplied"):
        parse_extraction_json(
            '{"incident_type":"collision","location_text":"X","severity":"high",'
            '"confidence":0.9,"latitude":12.0}'
        )
